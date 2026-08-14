from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView


class PreviewBridge(QObject):
    selected = Signal(str, str)

    @Slot(str, str)
    def element_selected(self, selector: str, tag: str) -> None:
        self.selected.emit(selector, tag)


class InteractivePreview(QWebEngineView):
    elementSelected = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bridge = PreviewBridge()
        self.bridge.selected.connect(self.elementSelected)
        self.channel = QWebChannel(self.page())
        self.channel.registerObject("siteforgeBridge", self.bridge)
        self.page().setWebChannel(self.channel)
        self.loadFinished.connect(self.install_selection_layer)

    @Slot(bool)
    def install_selection_layer(self, ok: bool) -> None:
        if not ok:
            return
        script = r"""
        (() => {
          if (window.__siteforgeSelectionInstalled) return;
          window.__siteforgeSelectionInstalled = true;
          const q = document.createElement('script');
          q.src = 'qrc:///qtwebchannel/qwebchannel.js';
          q.onload = () => new QWebChannel(qt.webChannelTransport, channel => {
            const bridge = channel.objects.siteforgeBridge;
            let selected = null;
            const selectorFor = el => {
              if (el.id) return '#' + CSS.escape(el.id);
              const classes = [...el.classList].filter(Boolean).slice(0,2);
              if (classes.length) return '.' + classes.map(CSS.escape).join('.');
              let index = 1, node = el;
              while ((node = node.previousElementSibling)) if (node.tagName === el.tagName) index++;
              return el.tagName.toLowerCase() + ':nth-of-type(' + index + ')';
            };
            const clear = () => { if(selected) selected.style.outline=''; };
            document.addEventListener('mouseover', e => { if(e.target instanceof Element) e.target.style.outline='2px solid #8b7cff'; }, true);
            document.addEventListener('mouseout', e => { if(e.target instanceof Element && e.target !== selected) e.target.style.outline=''; }, true);
            document.addEventListener('click', e => {
              if (!(e.target instanceof Element)) return;
              e.preventDefault(); e.stopPropagation(); clear(); selected=e.target; selected.style.outline='2px solid #8b7cff';
              bridge.element_selected(selectorFor(selected), selected.tagName.toLowerCase());
            }, true);
          });
          document.head.appendChild(q);
        })();
        """
        self.page().runJavaScript(script)
