from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QStackedWidget,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget, QCheckBox)
from PySide6.QtWebEngineWidgets import QWebEngineView

from siteforge.core.database import Database, Website
from siteforge.core.app_info import APP_NAME, APP_VERSION, PUBLISHER
from siteforge.core.secure_store import SecureStore
from siteforge.providers.ai import AIClient, AIConfig
from siteforge.services.deployment import Publisher, backup_project, export_zip, validate_project, import_project, deployment_diff
from siteforge.services.site_builder import SiteBuilder, TEMPLATES
from siteforge.services.ai_repair import AIRepairService, RepairProposal
from siteforge.services.project_tools import VersionStore
from siteforge.services.visual_editor import VisualEditor
from siteforge.services.ai_generation import AIGenerationService
from siteforge.services.verification import verify_deployment
from siteforge.ui.preview import InteractivePreview

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "SiteForgeAI"
DB = Database(APP_DIR / "siteforge.db")
SECRETS = SecureStore(APP_DIR / "secrets.bin")


class Worker(QObject):
    progress = Signal(int, str)
    done = Signal(object)
    failed = Signal(str)
    def __init__(self, fn): super().__init__(); self.fn = fn; self.cancelled = False
    @Slot()
    def run(self):
        try: self.done.emit(self.fn(self.progress, lambda: self.cancelled))
        except Exception as e: self.failed.emit(str(e))
    def cancel(self): self.cancelled = True


class Card(QFrame):
    def __init__(self, title: str, value: str = "", parent=None):
        super().__init__(parent); self.setObjectName("card")
        box = QVBoxLayout(self); box.addWidget(QLabel(title)); self.value_label = QLabel(value); self.value_label.setObjectName("cardValue"); box.addWidget(self.value_label)

    def setText(self, value: str):
        self.value_label.setText(value)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.current: Website | None = None; self.worker = None; self.thread = None
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}"); self.resize(1440, 900); self.setMinimumSize(1100, 700)
        self.build_ui(); self.apply_theme(); self.refresh_websites()

    def build_ui(self):
        root = QWidget(); shell = QHBoxLayout(root); shell.setContentsMargins(0,0,0,0)
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); side = QVBoxLayout(sidebar); side.setContentsMargins(22,28,22,22)
        logo = QLabel("SITEFORGE <span style='color:#8b7cff'>AI</span>"); logo.setObjectName("logo"); logo.setTextFormat(Qt.RichText); side.addWidget(logo); side.addWidget(QLabel("AI WEBSITE STUDIO"), alignment=Qt.AlignLeft); side.addSpacing(28)
        self.nav = QListWidget(); self.nav.setObjectName("nav")
        for name in ["＋  New Chat", "⌂  Dashboard", "▣  My Websites", "✦  AI Generation", "▤  Website Editor", "◉  Visual Editing", "▦  Templates", "↥  Import Website", "⚙  AI Repair", "◎  SEO Analyzer", "✓  Validation", "↗  Deployment", "◷  History", "⚙  Settings", "✦  AI Assistant"]: self.nav.addItem(name)
        self.nav.currentRowChanged.connect(self.navigate)
        side.addWidget(self.nav); side.addStretch(); upgrade=QFrame(); upgrade.setObjectName("upgradeCard"); ul=QVBoxLayout(upgrade); up_title=QLabel("✦  Upgrade to Pro"); up_title.setObjectName("upgradeTitle"); ul.addWidget(up_title); ul.addWidget(QLabel("Unlock unlimited websites, custom domains and more.")); up_btn=QPushButton("Upgrade now  →"); up_btn.setObjectName("upgradeButton"); ul.addWidget(up_btn); side.addWidget(upgrade); workspace = QLabel("●  All systems operational"); workspace.setObjectName("workspaceStatus"); side.addWidget(workspace); profile=QLabel("A   Alex Johnson\n    alex@siteforge.ai"); profile.setObjectName("profileCard"); side.addWidget(profile)
        shell.addWidget(sidebar); self.pages = QStackedWidget(); shell.addWidget(self.pages, 1); self.setCentralWidget(root)
        self.nav.currentRowChanged.connect(self.navigate)
        self.pages.addWidget(self.dashboard_page()); self.pages.addWidget(self.create_page()); self.pages.addWidget(self.websites_page()); self.pages.addWidget(self.editor_page()); self.pages.addWidget(self.preview_page()); self.pages.addWidget(self.deploy_page()); self.pages.addWidget(self.history_page()); self.pages.addWidget(self.settings_page()); self.pages.addWidget(self.generation_page()); self.pages.addWidget(self.import_page()); self.pages.addWidget(self.repair_page()); self.pages.addWidget(self.seo_page()); self.pages.addWidget(self.validation_page()); self.pages.addWidget(self.assistant_page())
        self.nav.setCurrentRow(0)

    def dashboard_page(self):
        page = QWidget(); page.setObjectName("studioPage"); shell = QHBoxLayout(page); shell.setContentsMargins(26, 22, 26, 22); shell.setSpacing(18)
        center = QFrame(); center.setObjectName("studioCenter"); main = QVBoxLayout(center); main.setContentsMargins(28, 22, 28, 26); main.setSpacing(18)
        topbar = QHBoxLayout(); back = QPushButton("‹  Back to dashboard"); back.setObjectName("ghostButton"); topbar.addWidget(back); topbar.addStretch(); templates = QPushButton("▦  Templates"); templates.setObjectName("topButton"); templates.clicked.connect(lambda: self.nav.setCurrentRow(4)); topbar.addWidget(templates); more = QPushButton("•••"); more.setObjectName("iconButton"); topbar.addWidget(more); main.addLayout(topbar)
        intro = QVBoxLayout(); intro.setAlignment(Qt.AlignCenter); chat_label = QLabel("New Chat"); chat_label.setObjectName("chatLabel"); intro.addWidget(chat_label, alignment=Qt.AlignLeft); hello = QLabel("Hey there. <span style='color:#8e7cff'>Let's build something amazing.</span>"); hello.setObjectName("helloTitle"); hello.setTextFormat(Qt.RichText); intro.addSpacing(25); intro.addWidget(hello, alignment=Qt.AlignCenter); hint = QLabel("Describe your website idea and SiteForge AI will build it for you."); hint.setObjectName("helloHint"); intro.addWidget(hint, alignment=Qt.AlignCenter); main.addLayout(intro)
        prompt = QFrame(); prompt.setObjectName("promptBox"); prompt_layout = QVBoxLayout(prompt); self.dashboard_prompt = QPlainTextEdit(); self.dashboard_prompt.setPlaceholderText("Describe the website you want to build..."); self.dashboard_prompt.setFixedHeight(108); prompt_layout.addWidget(self.dashboard_prompt); prompt_tools = QHBoxLayout(); attach = QPushButton("⌕"); attach.setObjectName("smallIcon"); add = QPushButton("＋"); add.setObjectName("smallIcon"); mode = QComboBox(); mode.addItems(["✦  Smart generation", "Landing page", "Multi-page website"]); mode.setObjectName("modeCombo"); send = QPushButton("↑"); send.setObjectName("sendButton"); send.clicked.connect(self.use_dashboard_prompt); prompt_tools.addWidget(attach); prompt_tools.addWidget(add); prompt_tools.addWidget(mode); prompt_tools.addStretch(); prompt_tools.addWidget(send); prompt_layout.addLayout(prompt_tools); main.addWidget(prompt)
        quick = QLabel("Not sure where to start? Try one of these"); quick.setObjectName("quickHint"); main.addWidget(quick, alignment=Qt.AlignCenter); suggestions = QHBoxLayout(); suggestions.setSpacing(10); suggestions.addWidget(self.suggestion_card("◈", "Portfolio website", "Showcase your work", "portfolio")); suggestions.addWidget(self.suggestion_card("➤", "SaaS landing page", "Convert more visitors", "saas")); suggestions.addWidget(self.suggestion_card("▣", "Restaurant website", "Menu and reservations", "restaurant")); suggestions.addWidget(self.suggestion_card("▤", "Agency website", "Stand out online", "agency")); main.addLayout(suggestions)
        import_box = QFrame(); import_box.setObjectName("importBox"); import_layout = QVBoxLayout(import_box); import_icon = QLabel("✦"); import_icon.setObjectName("importIcon"); import_layout.addWidget(import_icon, alignment=Qt.AlignCenter); import_title = QLabel("Import a brief, document or screenshot"); import_title.setObjectName("importTitle"); import_layout.addWidget(import_title, alignment=Qt.AlignCenter); import_hint = QLabel("Drag and drop your file here, or click to browse"); import_hint.setObjectName("importHint"); import_layout.addWidget(import_hint, alignment=Qt.AlignCenter); import_btn = QPushButton("Browse files  →"); import_btn.setObjectName("browseButton"); import_btn.clicked.connect(self.import_site); import_layout.addWidget(import_btn, alignment=Qt.AlignCenter); main.addWidget(import_box); main.addStretch(); shell.addWidget(center, 1)
        right = QFrame(); right.setObjectName("studioRight"); rbox = QVBoxLayout(right); rbox.setContentsMargins(16, 18, 16, 18); rbox.setSpacing(14); tips = QFrame(); tips.setObjectName("tipsBox"); tl = QVBoxLayout(tips); tl.addWidget(QLabel("✦  Tips for better results"), alignment=Qt.AlignLeft); [tl.addWidget(QLabel("◌  " + text)) for text in ["Be specific about your requirements", "Mention the type of website", "Include key sections you need", "Share your brand preferences", "Add any reference websites"]]; learn = QPushButton("Learn more  →"); learn.setObjectName("learnButton"); tl.addWidget(learn); rbox.addWidget(tips); popular = QFrame(); popular.setObjectName("popularBox"); pl=QVBoxLayout(popular); ph=QHBoxLayout(); ph.addWidget(QLabel("Popular Templates")); ph.addStretch(); see=QPushButton("View all"); see.setObjectName("textButton"); see.clicked.connect(lambda: self.nav.setCurrentRow(4)); ph.addWidget(see); pl.addLayout(ph);         [pl.addWidget(self.template_row(label, color)) for label, color in [("SaaS Landing", "#7c6cff"), ("Portfolio Minimal", "#df9c57"), ("E-commerce", "#63c59b"), ("Agency Website", "#6d9dfb")]]; browse_all=QPushButton("Browse all templates  →"); browse_all.setObjectName("browseButton"); browse_all.clicked.connect(lambda: self.nav.setCurrentRow(4)); pl.addWidget(browse_all); rbox.addWidget(popular)
        chats=QFrame(); chats.setObjectName("recentChats"); cl=QVBoxLayout(chats); cl.addWidget(QLabel("Recent chats")); [cl.addWidget(QLabel("◌  " + text)) for text in ["Modern agency website", "SaaS landing page", "Restaurant website"]]; rbox.addWidget(chats); rbox.addStretch(); shell.addWidget(right)
        self.recent_projects = QHBoxLayout(); self.ai_status = QLabel("AI Provider  ·  Not configured"); self.storage_status = QLabel("Storage  ·  Healthy"); return page

    def suggestion_card(self, icon, title, caption, template):
        card = QPushButton(); card.setObjectName("suggestionCard"); lay=QHBoxLayout(card); icon_l=QLabel(icon); icon_l.setObjectName("suggestionIcon"); text=QVBoxLayout(); a=QLabel(title); a.setObjectName("suggestionTitle"); b=QLabel(caption); b.setObjectName("suggestionCaption"); text.addWidget(a); text.addWidget(b); lay.addWidget(icon_l); lay.addLayout(text); card.clicked.connect(lambda: self.apply_suggestion(template, title)); return card

    def apply_suggestion(self, template, title):
        self.template.setCurrentIndex(list(TEMPLATES).index(template) if template in TEMPLATES else 0); self.site_name.setText(title); self.site_desc.setPlainText("Create a polished " + title.lower() + " with a clear visual identity and responsive sections."); self.nav.setCurrentRow(1)

    def template_row(self, label, color):
        row=QPushButton(); row.setObjectName("templateRow"); lay=QHBoxLayout(row); thumb=QLabel("  "); thumb.setStyleSheet(f"background:{color};border-radius:6px;min-width:48px;min-height:34px"); lay.addWidget(thumb); info=QVBoxLayout(); name=QLabel(label); name.setObjectName("templateName"); category=QLabel("Website template"); category.setObjectName("templateCategory"); info.addWidget(name); info.addWidget(category); lay.addLayout(info); lay.addStretch(); lay.addWidget(QLabel("›")); row.clicked.connect(lambda: self.nav.setCurrentRow(4)); return row

    def action_card(self, icon, line1, line2, callback):
        card = QPushButton(); card.setObjectName("actionCard"); card.setMinimumHeight(128); layout = QVBoxLayout(card); layout.setContentsMargins(20, 18, 20, 18); icon_label = QLabel(icon); icon_label.setObjectName("actionIcon"); title = QLabel(line1); title.setObjectName("actionTitle"); caption = QLabel(line2); caption.setObjectName("actionCaption"); layout.addWidget(icon_label); layout.addSpacing(6); layout.addWidget(title); layout.addWidget(caption); card.clicked.connect(callback); return card

    def project_card(self, website):
        card = QFrame(); card.setObjectName("projectCard"); layout = QVBoxLayout(card); preview = QLabel("<span style='font-size:28px'>◒</span><br>Live preview"); preview.setObjectName("projectPreview"); preview.setTextFormat(Qt.RichText); preview.setAlignment(Qt.AlignCenter); name = QLabel(website.name); name.setObjectName("projectName"); meta = QLabel(website.template.title() + "  ·  Local project"); meta.setObjectName("projectMeta"); layout.addWidget(preview); layout.addSpacing(8); layout.addWidget(name); layout.addWidget(meta); card.mousePressEvent = lambda event: (setattr(self, "current", website), self.load_preview(), self.nav.setCurrentRow(5)); return card

    def navigate(self, row):
        mapping = {0: 0, 1: 0, 2: 2, 3: 8, 4: 3, 5: 4, 6: 1, 7: 9, 8: 10, 9: 11, 10: 12, 11: 5, 12: 6, 13: 7, 14: 13}
        self.pages.setCurrentIndex(mapping.get(row, 0))

    def generation_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("AI Website Generation", "Turn a brief into a plan, pages, sections, content and real files.")); steps=QHBoxLayout();
        for n,label in [("01","Plan"),("02","Pages"),("03","Design"),("04","Files"),("05","Validate")]: steps.addWidget(self.step_card(n,label))
        box.addLayout(steps); panel=QFrame(); panel.setObjectName("toolPanel"); pl=QVBoxLayout(panel); prompt=QPlainTextEdit(); prompt.setPlaceholderText("Create a modern Arabic restaurant website with menu, reservations and dark gold colors…"); prompt.setFixedHeight(145); pl.addWidget(prompt); generate=QPushButton("Generate website plan  →"); generate.clicked.connect(lambda: self.nav.setCurrentRow(1)); pl.addWidget(generate); box.addWidget(panel); box.addStretch(); return page

    def step_card(self, number, label):
        card=QFrame(); card.setObjectName("stepCard"); lay=QVBoxLayout(card); lay.addWidget(QLabel(number)); lay.addWidget(QLabel(label)); return card

    def import_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("Import Website", "Bring an existing HTML/CSS/JS project into SiteForge AI safely.")); drop=QFrame(); drop.setObjectName("dropPanel"); dl=QVBoxLayout(drop); dl.addWidget(QLabel("＋"), alignment=Qt.AlignCenter); dl.addWidget(QLabel("Drop your website folder or ZIP here"), alignment=Qt.AlignCenter); dl.addWidget(QLabel("SiteForge will analyze pages, assets and local links."), alignment=Qt.AlignCenter); choose=QPushButton("Choose Folder or ZIP"); choose.clicked.connect(self.import_site); dl.addWidget(choose, alignment=Qt.AlignCenter); box.addWidget(drop); summary=QFrame(); summary.setObjectName("toolPanel"); sl=QVBoxLayout(summary); sl.addWidget(QLabel("Import checklist")); [sl.addWidget(QLabel("✓  " + item)) for item in ["Detect HTML pages", "Discover CSS and JavaScript assets", "Create a local project backup", "Open the result in Live Preview"]]; box.addWidget(summary); box.addStretch(); return page

    def repair_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("AI Website Repair", "Find broken links, missing assets, SEO issues and responsive problems before applying a fix.")); bar=QHBoxLayout(); scan=QPushButton("Scan selected project"); scan.clicked.connect(self.run_repair_scan); bar.addWidget(scan); edit=QPushButton("Open in AI Editor"); edit.clicked.connect(lambda: self.nav.setCurrentRow(4)); bar.addWidget(edit); bar.addStretch(); box.addLayout(bar); self.repair_table=QTextBrowser(); self.repair_table.setPlaceholderText("Critical, warning and passed findings will appear here."); box.addWidget(self.repair_table); return page

    def run_repair_scan(self):
        if not self.current: self.repair_table.setText("Select a website first."); return
        findings=AIRepairService().inspect(Path(self.current.project_path)); self.repair_table.setText("\n\n".join(f"[{f.severity.upper()}] {f.category} · {f.file}\n{f.problem}\nProposed fix: {f.proposed_fix}" for f in findings) or "PASSED — no repair findings detected.")

    def seo_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("SEO Analyzer", "Review metadata, Open Graph, canonical URL, favicon, robots and image ALT text.")); score=QFrame(); score.setObjectName("scorePanel"); sl=QHBoxLayout(score); sl.addWidget(QLabel("SEO score")); score_value=QLabel("— / 100"); score_value.setObjectName("scoreValue"); sl.addWidget(score_value); box.addWidget(score); check=QTextBrowser(); check.setPlaceholderText("SEO results will appear after scanning the selected project."); box.addWidget(check); scan=QPushButton("Analyze SEO"); scan.clicked.connect(lambda: self.analyze_seo(check, score_value)); box.addWidget(scan); box.addStretch(); return page

    def analyze_seo(self, output, score):
        if not self.current: output.setText("Select a website first."); return
        issues=validate_project(Path(self.current.project_path)); critical=sum(i.severity=="error" for i in issues); warnings=sum(i.severity=="warning" for i in issues); value=max(0,100-critical*25-warnings*8); score.setText(f"{value} / 100"); output.setText("\n".join(f"[{i.severity.upper()}] {i.file}: {i.message}" for i in issues) or "PASSED — core SEO checks are healthy.")

    def validation_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("Validation", "Check HTML, CSS, JavaScript, links, assets, SEO and deployment readiness.")); self.validation_output=QTextBrowser(); box.addWidget(self.validation_output); run=QPushButton("Run full validation"); run.clicked.connect(self.run_full_validation); box.addWidget(run); box.addStretch(); return page

    def run_full_validation(self):
        if not self.current: self.validation_output.setText("Select a website first."); return
        issues=validate_project(Path(self.current.project_path)); critical=[i for i in issues if i.severity=="error"]; warnings=[i for i in issues if i.severity=="warning"]; self.validation_output.setText(f"CRITICAL  {len(critical)}\nWARNING   {len(warnings)}\nPASSED    {max(0,5-len(critical)-len(warnings))}\n\n"+"\n".join(f"[{i.severity.upper()}] {i.file}: {i.message}" for i in issues))

    def assistant_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("AI Assistant", "Ask about your project, files, SEO or the next deployment step.")); self.assistant_log=QTextBrowser(); self.assistant_log.setText("SiteForge Assistant\n\nI can help you understand the selected project and suggest the next safe action."); box.addWidget(self.assistant_log); row=QHBoxLayout(); self.assistant_input=QLineEdit(); self.assistant_input.setPlaceholderText("Ask about this project…"); ask=QPushButton("Ask"); ask.clicked.connect(self.ask_assistant); row.addWidget(self.assistant_input); row.addWidget(ask); box.addLayout(row); return page

    def ask_assistant(self):
        prompt=self.assistant_input.text().strip();
        if not prompt: return
        client=self.load_ai_client(); self.assistant_log.append(f"\nYou: {prompt}")
        if not client: self.assistant_log.append("Assistant: Configure a BYOK provider in Settings to ask the AI model."); return
        try: self.assistant_log.append("Assistant: " + client.complete("You are the local SiteForge project assistant. Be concise and safe.", prompt))
        except Exception as exc: self.assistant_log.append("Assistant error: " + str(exc))

    def create_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("Create Website", "Generate files locally; review every change before publishing.")); form=QFormLayout(); self.site_name=QLineEdit(); self.site_name.setPlaceholderText("Acme Studio"); self.site_desc=QPlainTextEdit(); self.site_desc.setFixedHeight(130); self.site_desc.setPlaceholderText("Describe the website, audience, language, sections and tone..."); self.template=QComboBox(); self.template.addItems([f"{k.title()} — {v['label']}" for k,v in TEMPLATES.items()]); self.project_path=QLineEdit(str(Path.home()/"SiteForge Sites")); browse=QPushButton("Browse"); browse.clicked.connect(self.pick_folder); row=QHBoxLayout(); row.addWidget(self.project_path); row.addWidget(browse); form.addRow("Website name",self.site_name); form.addRow("Description",self.site_desc); form.addRow("Template",self.template); form.addRow("Project folder",row); box.addLayout(form); self.create_status=QLabel(); box.addWidget(self.create_status); b=QPushButton("Generate local website"); b.clicked.connect(self.generate_site); box.addWidget(b); box.addStretch(); return page

    def websites_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("My Websites", "Manage local projects and their hosting profiles.")); row=QHBoxLayout(); self.import_btn=QPushButton("Import Folder / ZIP"); self.import_btn.clicked.connect(self.import_site); row.addWidget(self.import_btn); row.addStretch(); box.addLayout(row); self.websites_list=QListWidget(); self.websites_list.itemDoubleClicked.connect(self.open_selected); box.addWidget(self.websites_list); return page

    def editor_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("AI Editor", "Review proposed changes before applying them to the real project files.")); self.editor_instruction=QPlainTextEdit(); self.editor_instruction.setPlaceholderText("Example: Change the hero headline to: Build better digital experiences"); box.addWidget(self.editor_instruction); self.editor_status=QLabel("Select a website first."); box.addWidget(self.editor_status); row=QHBoxLayout(); b=QPushButton("Apply local edit"); b.clicked.connect(self.apply_edit); fix=QPushButton("Fix Website"); fix.clicked.connect(self.fix_website); row.addWidget(b); row.addWidget(fix); box.addLayout(row); self.repair_report=QTextBrowser(); self.repair_report.setPlaceholderText("Repair findings and proposed Diff will appear here."); box.addWidget(self.repair_report); self.apply_repair_btn=QPushButton("Apply Proposed Changes"); self.apply_repair_btn.clicked.connect(self.apply_repair); self.apply_repair_btn.setEnabled(False); box.addWidget(self.apply_repair_btn); return page

    def preview_page(self):
        page=QWidget(); root=QVBoxLayout(page); root.addWidget(self.header("AI Studio", "Click anything in the live website, tell AI what to change, then apply it to the real files.")); top=QHBoxLayout(); top.addWidget(QLabel("Live website preview")); top.addStretch(); self.viewport=QComboBox(); self.viewport.addItems(["Desktop","Tablet","Mobile"]); self.viewport.currentTextChanged.connect(self.resize_preview); top.addWidget(self.viewport); refresh=QPushButton("↻ Refresh"); refresh.clicked.connect(self.load_preview); top.addWidget(refresh); open_btn=QPushButton("Open in browser"); open_btn.clicked.connect(self.open_browser); top.addWidget(open_btn); root.addLayout(top)
        workspace=QHBoxLayout(); files=QFrame(); files.setObjectName("filesPanel"); files.setFixedWidth(190); fl=QVBoxLayout(files); fl.addWidget(QLabel("Project files")); [fl.addWidget(QLabel(item)) for item in ["⌄  index.html","◌  style.css","◌  script.js","⌁  assets/","◌  favicon.ico","◌  sitemap.xml"]]; fl.addStretch(); workspace.addWidget(files)
        center=QVBoxLayout(); selectbar=QHBoxLayout(); self.visual_selector=QLineEdit(); self.visual_selector.setPlaceholderText("Click an element in the preview…"); self.visual_selector.setReadOnly(True); self.visual_tag=QLabel("No element selected"); self.visual_tag.setObjectName("selectedTag"); selectbar.addWidget(self.visual_selector,1); selectbar.addWidget(self.visual_tag); center.addLayout(selectbar); self.preview_status=QLabel("Click an element to begin editing."); self.preview_status.setObjectName("previewStatus"); center.addWidget(self.preview_status); self.preview=InteractivePreview(); self.preview.elementSelected.connect(self.on_preview_element_selected); center.addWidget(self.preview,1); workspace.addLayout(center,1)
        assistant=QFrame(); assistant.setObjectName("aiAssistantPanel"); assistant.setFixedWidth(285); al=QVBoxLayout(assistant); al.addWidget(QLabel("✦  AI Website Editor")); self.preview_ai_log=QTextBrowser(); self.preview_ai_log.setObjectName("assistantLog"); self.preview_ai_log.setText("Select an element in the preview.\n\nAI will explain the proposed change before anything is applied."); al.addWidget(self.preview_ai_log,1); self.visual_instruction=QLineEdit(); self.visual_instruction.setPlaceholderText("Tell AI what to change…"); al.addWidget(self.visual_instruction); ask=QPushButton("✦ Ask AI"); ask.clicked.connect(self.preview_ask_ai); al.addWidget(ask); buttons=QHBoxLayout(); apply=QPushButton("Apply Changes"); apply.clicked.connect(self.apply_preview_change); apply.setObjectName("applyButton"); undo=QPushButton("Undo"); undo.clicked.connect(self.undo_preview_change); redo=QPushButton("Redo"); redo.clicked.connect(self.redo_preview_change); buttons.addWidget(apply); buttons.addWidget(undo); buttons.addWidget(redo); al.addLayout(buttons); workspace.addWidget(assistant); root.addLayout(workspace,1); return page

    def deploy_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("Deploy", "Validate, backup, then upload through your configured hosting connection.")); self.deploy_form=QFormLayout(); self.protocol=QComboBox(); self.protocol.addItems(["SFTP","FTP","FTPS","cPanel","DirectAdmin"]); self.host=QLineEdit(); self.port=QLineEdit("22"); self.username=QLineEdit(); self.password=QLineEdit(); self.password.setEchoMode(QLineEdit.Password); self.api_token=QLineEdit(); self.api_token.setEchoMode(QLineEdit.Password); self.base_url=QLineEdit(); self.verify_url=QLineEdit(); self.remote=QLineEdit("/"); self.deploy_form.addRow("Protocol",self.protocol); self.deploy_form.addRow("Host",self.host); self.deploy_form.addRow("Port",self.port); self.deploy_form.addRow("Username",self.username); self.deploy_form.addRow("Password",self.password); self.deploy_form.addRow("API token",self.api_token); self.deploy_form.addRow("API base URL",self.base_url); self.deploy_form.addRow("Verify URL",self.verify_url); self.deploy_form.addRow("Remote path",self.remote); box.addLayout(self.deploy_form); self.deploy_progress=QProgressBar(); box.addWidget(self.deploy_progress); self.deploy_status=QLabel(); box.addWidget(self.deploy_status); row=QHBoxLayout(); validate=QPushButton("Validate project"); validate.clicked.connect(self.validate); deploy=QPushButton("Backup & Deploy"); deploy.clicked.connect(self.deploy); export=QPushButton("Export ZIP"); export.clicked.connect(self.export); row.addWidget(validate); row.addWidget(deploy); row.addWidget(export); box.addLayout(row); self.issues=QTextBrowser(); box.addWidget(self.issues); return page

    def history_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("Version & Deployment History", "Restore a reviewed local version or inspect deployment records.")); self.history=QTextBrowser(); box.addWidget(self.history); row=QHBoxLayout(); refresh=QPushButton("Refresh"); refresh.clicked.connect(self.refresh_history); restore=QPushButton("Restore Selected Version"); restore.clicked.connect(self.restore_version); row.addWidget(refresh); row.addWidget(restore); box.addLayout(row); return page
    def settings_page(self):
        page=QWidget(); box=QVBoxLayout(page); box.addWidget(self.header("Settings", "Configure provider keys locally; values are encrypted at rest.")); form=QFormLayout(); self.provider=QComboBox(); self.provider.addItems(["OpenAI","Gemini","Claude","OpenRouter"]); self.model=QLineEdit("gpt-4o-mini"); self.api_key=QLineEdit(); self.api_key.setEchoMode(QLineEdit.Password); form.addRow("AI provider",self.provider); form.addRow("Model",self.model); form.addRow("API key",self.api_key); box.addLayout(form); self.light_mode=QCheckBox("Light mode"); self.rtl_mode=QCheckBox("Arabic RTL"); self.light_mode.stateChanged.connect(self.toggle_theme); self.rtl_mode.stateChanged.connect(self.toggle_rtl); box.addWidget(self.light_mode); box.addWidget(self.rtl_mode); save=QPushButton("Save encrypted settings"); save.clicked.connect(self.save_settings); box.addWidget(save); box.addWidget(QLabel("Keys are stored in the user profile, never in source code or generated websites.")); box.addStretch(); return page

    def header(self, title, subtitle):
        w=QFrame(); w.setObjectName("pageHeader"); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,18); crumb=QLabel("SITEFORGE AI  /  WORKSPACE"); crumb.setObjectName("headerCrumb"); l.addWidget(crumb); row=QHBoxLayout(); a=QLabel(title); a.setObjectName("pageTitle"); row.addWidget(a); row.addStretch(); live=QLabel("●  Local workspace"); live.setObjectName("headerStatus"); row.addWidget(live); l.addLayout(row); sub=QLabel(subtitle); sub.setObjectName("headerSubtitle"); l.addWidget(sub); return w
    def use_dashboard_prompt(self):
        self.site_desc.setPlainText(self.dashboard_prompt.toPlainText())
        self.nav.setCurrentRow(1)

    def import_site(self):
        source, _ = QFileDialog.getOpenFileName(self, "Import ZIP (Cancel for folder)", "", "ZIP (*.zip)")
        if not source:
            source = QFileDialog.getExistingDirectory(self, "Import website folder")
        if not source: return
        name = Path(source).stem.replace("_", " ").replace("-", " ").title()
        target = Path.home() / "SiteForge Sites" / name.lower().replace(" ", "-")
        try:
            imported = import_project(Path(source), target)
            self.current = DB.create_website(name, "Imported website", str(imported), "imported")
            self.refresh_websites(); QMessageBox.information(self, "Imported", f"Imported to {imported}")
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))

    def pick_folder(self):
        p=QFileDialog.getExistingDirectory(self,"Choose project folder");
        if p: self.project_path.setText(p)
    def selected_template(self): return list(TEMPLATES)[self.template.currentIndex()]
    def generate_site(self):
        name=self.site_name.text().strip(); desc=self.site_desc.toPlainText().strip(); path=Path(self.project_path.text()).expanduser()/name.replace(" ","-").lower()
        if not name: QMessageBox.warning(self,"Missing name","Enter a website name."); return
        if path.exists() and any(path.iterdir()): QMessageBox.warning(self,"Project exists","Choose a new project name or import the existing project."); return
        client = self.load_ai_client()
        self.create_status.setText("Generating a plan and real files…")
        def job(progress, cancel):
            progress(10, "Building website plan")
            result=AIGenerationService(client).generate(path, desc)
            progress(100, f"Wrote {len(result['files'])} files")
            return result
        self.start_generation_worker(job, name, desc, path)

    def start_generation_worker(self, fn, name, desc, path):
        self.thread=QThread(); self.worker=Worker(fn); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(lambda n,m: self.create_status.setText(m))
        def done(result):
            self.current=DB.create_website(name,desc,str(path),self.selected_template()); self.create_status.setText(f"Generated {len(result['files'])} real files at {path}"); self.refresh_websites(); self.load_preview(); self.nav.setCurrentRow(4); self.thread.quit()
        self.worker.done.connect(done); self.worker.failed.connect(lambda e:(QMessageBox.critical(self,"Generation failed",e), self.create_status.setText("Generation failed"), self.thread.quit())); self.thread.start()
    def refresh_websites(self):
        if not hasattr(self,'websites_list'): return
        self.websites_list.clear(); sites=DB.list_websites()
        if hasattr(self, "recent_projects"):
            while self.recent_projects.count():
                item=self.recent_projects.takeAt(0); item.widget().deleteLater() if item.widget() else None
            for site in sites[:3]: self.recent_projects.addWidget(self.project_card(site))
            for _ in range(max(0, 3-len(sites))):
                empty=QFrame(); empty.setObjectName("projectCard"); empty_layout=QVBoxLayout(empty); empty_label=QLabel("No recent website"); empty_label.setObjectName("emptyProject"); empty_label.setAlignment(Qt.AlignCenter); empty_layout.addWidget(empty_label); self.recent_projects.addWidget(empty)
            self.ai_status.setText("AI Provider: Configured ✓" if SECRETS.get("ai") and SECRETS.get("ai").get("api_key") else "AI Provider: Not configured")
        for s in sites: item=QListWidgetItem(f"{s.name}  ·  {s.template}  ·  {s.project_path}"); item.setData(32,s); self.websites_list.addItem(item)
    def open_selected(self,item): self.current=item.data(32); self.load_preview(); self.nav.setCurrentRow(4)
    def load_preview(self):
        if self.current: self.preview.setUrl(QUrl.fromLocalFile(str(Path(self.current.project_path)/"index.html")))
    def resize_preview(self, mode):
        widths={"Desktop":1100,"Tablet":768,"Mobile":390}; self.preview.setMinimumWidth(widths[mode])
    def open_browser(self):
        if self.current: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.current.project_path)/"index.html")))

    def on_preview_element_selected(self, selector, tag):
        self.visual_selector.setText(selector); self.visual_tag.setText(f"<{tag}>"); self.preview_status.setText(f"Selected {selector}. Describe the change and press Ask AI."); self.preview_ai_log.setText(f"Selected element\n{selector}\n\nWhat would you like to change?")

    def preview_ask_ai(self):
        if not self.current: QMessageBox.warning(self,"No website","Open or create a website first."); return
        if not self.visual_selector.text(): QMessageBox.warning(self,"Select an element","Click an element in Live Preview first."); return
        instruction=self.visual_instruction.text().strip()
        if not instruction: return
        client=self.load_ai_client(); selector=self.visual_selector.text(); root=Path(self.current.project_path)
        if client is None:
            lower=instruction.lower(); kind="delete" if any(x in lower for x in ["delete", "remove", "احذف", "إزالة"]) else ("image" if any(x in lower for x in ["image", "photo", "صورة"]) else ("text" if any(x in lower for x in ["text", "title", "heading", "نص", "عنوان"]) else "style"))
            self.preview_change={"selector":selector,"instruction":instruction,"type":kind}
            self.preview_status.setText("Local edit proposal ready. Configure a BYOK provider to ask an AI model; nothing has been applied.")
            return
        self.preview_status.setText("AI is analyzing the selected element…")
        def job(progress, cancel):
            html_content=(root/"index.html").read_text(encoding="utf-8", errors="replace")[:24000]
            css_content=(root/"style.css").read_text(encoding="utf-8", errors="replace")[:24000] if (root/"style.css").exists() else ""
            raw=client.complete("Return only JSON with keys type, property, value, text, url, alt. type is text, style, delete, or image. property must be one of color, background-color, font-size, padding, border-radius, text-align, direction.", f"Selected selector: {selector}\nUser request: {instruction}\nHTML:\n{html_content}\nCSS:\n{css_content}")
            raw=raw.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(raw)
        self.thread=QThread(); self.worker=Worker(job); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run)
        self.worker.done.connect(lambda proposal:(self.set_preview_proposal(proposal, selector, instruction), self.thread.quit()))
        self.worker.failed.connect(lambda error:(QMessageBox.critical(self,"AI edit failed",error), self.preview_status.setText("AI edit failed"), self.thread.quit())); self.thread.start()

    def set_preview_proposal(self, proposal, selector, instruction):
        proposal["selector"]=selector; proposal["instruction"]=instruction; self.preview_change=proposal; self.preview_status.setText(f"AI proposal ready: {proposal.get('type','style')} edit. Review then press Apply Changes."); self.preview_ai_log.setText(f"User\n{instruction}\n\nAI Website Editor\nI found {selector}.\n\nChanges detected\n1 element affected\n{proposal.get('type','style')} change\n\nReview the preview, then Apply Changes.")

    def apply_preview_change(self):
        if not self.current or not getattr(self, "preview_change", None): return
        root=Path(self.current.project_path)
        try:
            change=self.preview_change; editor=VisualEditor(root)
            if change.get("type") == "text":
                text=change.get("text") or change.get("instruction", ""); changed=editor.edit_text(change["selector"], text, "Live Preview AI text edit")
            elif change.get("type") == "delete":
                changed=editor.remove_element(change["selector"], "Live Preview AI remove element")
            elif change.get("type") == "image":
                changed=editor.add_image(change["selector"], change.get("url") or "https://images.unsplash.com/photo-1497366754035-f200968a6e72", change.get("alt") or "Website image", "Live Preview AI add image")
            else:
                property_name=change.get("property"); value=change.get("value")
                if not property_name or not value: property_name, value = self.infer_style_change(change.get("instruction", ""))
                changed=editor.edit_style(change["selector"], property_name, value, "Live Preview AI style edit")
            after=VersionStore(root).create("After Live Preview AI edit"); self.last_preview_version=after.name
            self.preview_status.setText(f"Applied to real files: {', '.join(changed)}. Preview updated."); self.load_preview(); self.preview_change=None; self.refresh_history()
        except Exception as exc: QMessageBox.warning(self,"Apply failed",str(exc))

    def infer_style_change(self, instruction):
        text=instruction.lower()
        if "blue" in text or "أزرق" in text: return "background-color", "#2563eb"
        if "red" in text or "أحمر" in text: return "background-color", "#dc2626"
        if "green" in text or "أخضر" in text: return "background-color", "#16a34a"
        if "larger" in text or "كبّر" in text or "اكبر" in text: return "font-size", "clamp(28px, 6vw, 72px)"
        if "rtl" in text or "يمين" in text: return "direction", "rtl"
        return "color", "#8b7cff"

    def undo_preview_change(self):
        if not self.current: return
        versions=VersionStore(Path(self.current.project_path)).list()
        if len(versions) < 2: self.preview_status.setText("No previous Live Preview change to undo."); return
        target=versions[1]["id"]; VersionStore(Path(self.current.project_path)).restore(target); self.undo_version=target; self.load_preview(); self.preview_status.setText("Undone: restored the previous real project version.")

    def redo_preview_change(self):
        if not self.current or not getattr(self, "last_preview_version", None): self.preview_status.setText("No Live Preview change available to redo."); return
        VersionStore(Path(self.current.project_path)).restore(self.last_preview_version); self.load_preview(); self.preview_status.setText("Redone: restored the applied Live Preview version.")

    def visual_edit(self):
        if not self.current: QMessageBox.warning(self,"No website","Select a website first."); return
        try:
            editor=VisualEditor(Path(self.current.project_path)); changed=editor.edit_text(self.visual_selector.text(), self.visual_text.text()); self.editor_status.setText(f"Visual edit changed {len(changed)} file(s) and created a version."); self.load_preview(); self.refresh_history()
        except Exception as exc: QMessageBox.warning(self,"Visual edit","Select a supported text element selector and provide new text.\n"+str(exc))
    def load_ai_client(self):
        saved = SECRETS.get("ai") or {}
        if not saved.get("api_key"): return None
        return AIClient(AIConfig(saved.get("provider", "OpenAI"), saved["api_key"], saved.get("model", "gpt-4o-mini"), saved.get("base_url", "")))

    def apply_edit(self):
        if not self.current: QMessageBox.warning(self,"No website","Select a website first."); return
        root=Path(self.current.project_path); VersionStore(root).create("Manual/AI editor change")
        changed=SiteBuilder().apply_text_edit(root,self.editor_instruction.toPlainText()); self.editor_status.setText(f"Changed {len(changed)} file(s) after creating a version backup."); DB.touch(self.current.id); self.load_preview(); self.refresh_history()

    def fix_website(self):
        if not self.current: QMessageBox.warning(self,"No website","Select a website first."); return
        root=Path(self.current.project_path); self.repair_proposal = None
        try:
            service=AIRepairService(self.load_ai_client()); proposal=service.propose(root,self.editor_instruction.toPlainText()); self.repair_proposal=proposal
            report=[f"{f.severity.upper()} · {f.category} · {f.file}\n{f.problem}\nExplanation: {f.explanation}\nProposed fix: {f.proposed_fix}" for f in proposal.findings]
            if proposal.diff: report.append("\n--- PROPOSED DIFF ---\n"+proposal.diff)
            self.repair_report.setPlainText("\n\n".join(report) or "No repair findings detected.")
            self.apply_repair_btn.setEnabled(bool(proposal.changed_files)); self.editor_status.setText("Review the findings and Diff. Nothing has been applied.")
        except Exception as exc: QMessageBox.critical(self,"Repair failed",str(exc))

    def apply_repair(self):
        if not self.current or not getattr(self,"repair_proposal",None): return
        proposal=self.repair_proposal; VersionStore(Path(self.current.project_path)).create("Before applying AI repair")
        applied=AIRepairService().apply(Path(self.current.project_path),proposal); self.editor_status.setText(f"Applied {len(applied)} reviewed file changes."); self.apply_repair_btn.setEnabled(False); self.load_preview(); self.refresh_history()
    def validate(self):
        if not self.current: return
        issues=validate_project(Path(self.current.project_path)); self.issues.setText("\n".join(f"[{i.severity.upper()}] {i.file}: {i.message}" for i in issues) or "PASS — no blocking issues found.")
    def export(self):
        if not self.current: return
        p,_=QFileDialog.getSaveFileName(self,"Export website ZIP",self.current.name+".zip","ZIP (*.zip)");
        if p: export_zip(Path(self.current.project_path),Path(p)); self.deploy_status.setText("ZIP exported successfully.")
    def deploy(self):
        if not self.current: return
        root=Path(self.current.project_path); issues=validate_project(root); errors=[i for i in issues if i.severity=="error"]
        if errors: self.issues.setText("Fix blocking issues before deployment.\n"+"\n".join(i.message for i in errors)); return
        if QMessageBox.question(self,"Confirm deployment","Create a local backup and upload the reviewed project now?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes: return
        latest=VersionStore(root).list(); remote_manifest=latest[0].get("manifest",{}) if latest else {}
        diff=deployment_diff(root,remote_manifest); summary=f"Modified: {len(diff['modified'])} | New: {len(diff['new'])} | Deleted: {len(diff['deleted'])}"
        self.issues.setText(summary+"\n\n"+"\n".join(diff["modified"]+diff["new"]+diff["deleted"]))
        if diff["deleted"] and QMessageBox.question(self,"Deleted remote files","The deployment diff contains deleted files. Confirm explicit remote deletion?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes: return
        backup=str(backup_project(root,APP_DIR/"backups")); cfg={"protocol":self.protocol.currentText().lower(),"host":self.host.text(),"port":self.port.text(),"username":self.username.text(),"password":self.password.text(),"api_token":self.api_token.text(),"base_url":self.base_url.text(),"verify_url":self.verify_url.text(),"remote_path":self.remote.text()};
        def publish_and_verify(progress, cancel):
            uploaded=Publisher().publish(root,cfg,progress,cancel)
            verification=verify_deployment(root,cfg.get("verify_url") or None)
            if not verification.ok: raise RuntimeError(uploaded + " | Verification failed: " + verification.message)
            return uploaded + " | " + verification.message
        self.start_worker(publish_and_verify, backup, cfg["protocol"], cfg["remote_path"])
    def start_worker(self, fn, backup="", provider="", remote_path=""):
        self.thread=QThread(); self.worker=Worker(fn); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.progress.connect(lambda n,m:(self.deploy_progress.setValue(n),self.deploy_status.setText(m)))
        def completed(result):
            self.deploy_status.setText(str(result));
            if self.current: DB.record_deployment(self.current.id, provider, "success", remote_path, backup, str(result))
            self.thread.quit(); self.refresh_history()
        def failed(error):
            if self.current: DB.record_deployment(self.current.id, provider, "failure", remote_path, backup, str(error))
            QMessageBox.critical(self,"Operation failed",error); self.thread.quit(); self.refresh_history()
        self.worker.done.connect(completed); self.worker.failed.connect(failed); self.thread.start()
    def refresh_history(self):
        if not self.current: return
        root=Path(self.current.project_path); versions=VersionStore(root).list(); deployments=DB.deployments(self.current.id)
        lines=["VERSIONS", "========"]
        lines += [f"{v['id']} — {v.get('message','')} — {v.get('created_at','')}" for v in versions] or ["No versions yet."]
        lines += ["", "DEPLOYMENTS", "==========="]
        lines += [str(x) for x in deployments] or ["No deployments yet."]
        self.history.setText("\n".join(lines))

    def restore_version(self):
        if not self.current: return
        versions=VersionStore(Path(self.current.project_path)).list()
        if not versions: QMessageBox.information(self,"No versions","Create a version by editing or repairing the project first."); return
        selected=versions[0]
        if QMessageBox.question(self,"Restore version",f"Restore latest version {selected['id']}? A backup will be created first.",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes: return
        store=VersionStore(Path(self.current.project_path)); store.create("Before restore"); store.restore(selected["id"]); self.load_preview(); self.refresh_history(); QMessageBox.information(self,"Restored","The selected version has been restored.")
    def toggle_theme(self):
        if self.light_mode.isChecked(): self.setStyleSheet("QWidget{font-family:'Segoe UI';font-size:14px;color:#1f2937;background:#f7f9fc} QFrame#sidebar{background:#e8eef8} QLineEdit,QPlainTextEdit,QTextBrowser,QComboBox{background:#fff;border:1px solid #cbd5e1;border-radius:8px;padding:9px;color:#111827} QPushButton{background:#2563eb;border:0;border-radius:8px;padding:11px 18px;color:#fff;font-weight:700}")
        else: self.apply_theme()

    def toggle_rtl(self):
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if self.rtl_mode.isChecked() else Qt.LeftToRight)

    def save_settings(self):
        SECRETS.set("ai",{"provider":self.provider.currentText(),"model":self.model.text(),"api_key":self.api_key.text()}); DB.set_setting("light_mode", str(self.light_mode.isChecked())); DB.set_setting("rtl_mode", str(self.rtl_mode.isChecked())); QMessageBox.information(self,"Saved","Encrypted AI settings saved locally.")
    def apply_theme(self):
        self.setStyleSheet("""
        QWidget{font-family:'Segoe UI';font-size:14px;color:#d9e2f1;background:#0b1020}
        #studioPage{background:#080d1a}
        #studioCenter{background:#0b1020;border:1px solid #1a263b;border-radius:16px}
        #studioRight{background:#0d1424;border:1px solid #1a263b;border-radius:16px;min-width:270px;max-width:310px}
        #ghostButton,#topButton,#iconButton{background:transparent;border:1px solid #202d45;color:#8595ad;border-radius:8px;padding:8px 12px}
        #ghostButton:hover,#topButton:hover,#iconButton:hover{background:#151f35;color:#fff;border-color:#3a4d70}
        #chatLabel{font-size:15px;font-weight:700;color:#dfe7f5}
        #helloTitle{font-size:28px;font-weight:750;color:#f4f6ff}
        #helloHint,#quickHint{font-size:13px;color:#7586a3}
        #promptBox{background:#111a2b;border:1px solid #2b3b58;border-radius:13px;padding:5px}
        #promptBox QPlainTextEdit{background:transparent;border:0;padding:12px;color:#eaf0fb;font-size:14px}
        #smallIcon{background:transparent;border:0;color:#8595ad;font-size:18px;padding:5px}
        #modeCombo{background:#19243a;border:0;border-radius:7px;padding:6px 10px;color:#aab7ca}
        #sendButton{background:#816df4;border:0;border-radius:20px;color:#fff;font-size:21px;min-width:38px;min-height:38px}
        #sendButton:hover{background:#9a88ff}
        #suggestionCard{background:#111a2c;border:1px solid #20314e;border-radius:10px;text-align:left;padding:10px;color:#e7eef9;min-height:74px}
        #suggestionCard:hover{background:#17233c;border-color:#6d5fea}
        #suggestionCard QLabel{background:transparent}
        #suggestionIcon{font-size:18px;color:#8b7cff}
        #suggestionTitle{font-size:12px;font-weight:700;color:#f4f6ff}
        #suggestionCaption{font-size:10px;color:#7b8ba6}
        #importBox{background:#0f1729;border:1px dashed #314568;border-radius:13px;padding:20px;min-height:105px}
        #importIcon{font-size:22px;color:#8b7cff}
        #importTitle{font-size:14px;font-weight:700;color:#dfe8f7}
        #importHint{font-size:11px;color:#71839e}
        #browseButton,#learnButton{background:#17233a;border:1px solid #2a3c5c;border-radius:8px;color:#a99fff;padding:8px 12px}
        #browseButton:hover,#learnButton:hover{background:#243355;border-color:#7669ef}
        #tipsBox,#popularBox{background:#10192b;border:1px solid #1d2d48;border-radius:12px;padding:6px}
        #tipsBox QLabel,#popularBox QLabel{background:transparent;color:#8b9ab0;font-size:11px;padding:5px}
        #templateRow{background:transparent;border:0;border-radius:7px;text-align:left;padding:4px;color:#d5deec}
        #templateRow:hover{background:#182640}
        #templateRow QLabel{font-size:12px;color:#cbd7e8;background:transparent} #templateName{font-weight:700;color:#e7eefb!important} #templateCategory{font-size:10px!important;color:#71839e!important} #recentChats{background:#10192b;border:1px solid #1d2d48;border-radius:12px;padding:5px} #recentChats QLabel{background:transparent;color:#8c9bb2;font-size:11px;padding:4px}

        #sidebar{background:#0a0f1d;border-right:1px solid #202b42}
        #logo{font-size:23px;font-weight:800;letter-spacing:1px;color:#f7f9ff}
        #logo+QLabel{color:#657590;font-size:9px;letter-spacing:1.5px}
        #sidebar>QLabel{color:#657590;font-size:10px;letter-spacing:1.5px}
        #workspaceStatus{color:#78d6a3;font-size:10px;padding:10px 12px;background:#10182b;border:1px solid #1d2a43;border-radius:10px}
        #upgradeCard{background:#18143b;border:1px solid #40357b;border-radius:12px;padding:5px}
        #upgradeCard QLabel{background:transparent;color:#9a91c9;font-size:10px;padding:3px}
        #upgradeTitle{color:#e8e3ff!important;font-size:12px!important;font-weight:700}
        #upgradeButton{background:#725ff0;border:0;border-radius:7px;padding:7px;color:#fff;font-size:11px}
        #profileCard{background:transparent;color:#a7b3c7;font-size:11px;padding:10px 2px}

        #nav{border:0;background:transparent;outline:0}
        #nav::item{padding:12px 13px;border-radius:9px;margin:3px 0;color:#7f90aa}
        #nav::item:hover{background:#121d32;color:#dce7f8}
        #nav::item:selected{background:#25204b;color:#fff;border-left:3px solid #8b7cff}
        #dashboardPage{background:#0b1020}
        #pageHeader{background:transparent;border-bottom:1px solid #1a263b}
        #headerCrumb{font-size:10px;letter-spacing:2px;color:#7f72e8;font-weight:700}
        QLabel#pageTitle{font-size:30px;font-weight:800;color:#f4f7ff}
        #headerSubtitle{color:#8291aa;font-size:13px}
        #headerStatus{color:#72d3a0;font-size:11px;background:#102319;border:1px solid #214a37;border-radius:9px;padding:7px 10px}

        QLabel#eyebrow{font-size:11px;letter-spacing:2px;color:#8b7cff;font-weight:700}
        QLabel#greeting{font-size:42px;font-weight:800;color:#f8faff;line-height:1.05}
        QLabel#dashboardSubtitle{font-size:16px;color:#8291aa;max-width:580px}
        QFrame#aiBadge{background:#171531;border:1px solid #3c3470;border-radius:14px;min-width:190px;padding:12px;color:#a79cff}
        QFrame#aiBadge QLabel{background:transparent;color:#9f94ff;font-size:10px;letter-spacing:1.5px}
        QLabel#badgeValue{color:#f6f4ff;font-size:17px;font-weight:700;letter-spacing:0}
        QLabel#sectionTitle{font-size:19px;font-weight:750;color:#f5f7ff}
        QPushButton#textButton{background:transparent;border:0;color:#8e83ff;padding:4px;font-weight:600}
        QPushButton#actionCard{background:#111a2d;border:1px solid #223451;border-radius:14px;text-align:left;padding:18px;color:#eaf1ff}
        QPushButton#actionCard:hover{background:#172440;border:1px solid #6c5ff0}
        QPushButton#actionCard QLabel{background:transparent} QLabel#actionIcon{font-size:24px;color:#9b8dff}
        QLabel#actionTitle{font-size:17px;font-weight:750;color:#f7f9ff}
        QLabel#actionCaption{font-size:12px;color:#7d8da7}
        QFrame#projectCard{background:#111a2d;border:1px solid #21324f;border-radius:14px;min-width:190px;max-width:280px;padding:8px}
        QFrame#projectCard:hover{border:1px solid #5f54d8;background:#151f38}
        QLabel#projectPreview{background:#0d1526;border-radius:9px;min-height:104px;color:#7d75d8} QLabel#projectName,QLabel#projectMeta,QLabel#emptyProject{background:transparent}
        QLabel#projectName{font-size:16px;font-weight:700;color:#f5f7ff;margin-top:4px}
        QLabel#projectMeta,#emptyProject{color:#7486a2;font-size:12px}
        QFrame#statusPanel{background:#10182a;border:1px solid #1e2d48;border-radius:11px;padding:8px;color:#8a9bb5}
        QLineEdit,QPlainTextEdit,QTextBrowser,QComboBox{background:#0f182b;border:1px solid #263753;border-radius:9px;padding:9px;color:#e7eef9}
        QPushButton{background:#6658e8;border:0;border-radius:9px;padding:11px 18px;color:#fff;font-weight:700}
        QPushButton:hover{background:#786cff}
        QProgressBar{border:1px solid #263753;border-radius:6px;text-align:center}
        QProgressBar::chunk{background:#6658e8;border-radius:6px}
        #selectedTag{background:#18143b;border:1px solid #40357b;border-radius:8px;color:#aaa0ff;padding:8px 12px} #previewStatus{color:#8e9db4;font-size:12px;padding:3px} #applyButton{background:#725ff0} #applyButton:hover{background:#8b7cff}
        #selectedTag{background:#18143b;border:1px solid #40357b;border-radius:8px;color:#aaa0ff;padding:8px 12px} #previewStatus{color:#8e9db4;font-size:12px;padding:3px} #applyButton{background:#725ff0} #applyButton:hover{background:#8b7cff}
        #filesPanel,#aiAssistantPanel{background:#0e1728;border:1px solid #1d2d49;border-radius:12px;padding:8px} #filesPanel QLabel{color:#8091aa;padding:7px 4px;font-size:12px} #filesPanel QLabel:first-child{color:#f4f7ff;font-weight:700;font-size:13px;padding-bottom:14px} #aiAssistantPanel>QLabel{color:#f1efff;font-weight:700;padding:5px} #assistantLog{background:#0b1424;border:1px solid #213453;border-radius:9px;color:#9eacc2;font-size:12px;padding:10px} #toolPanel,#dropPanel,#scorePanel{background:#101a2d;border:1px solid #1f3150;border-radius:12px;padding:14px} #stepCard{background:#111b2d;border:1px solid #253858;border-radius:10px;padding:5px} #stepCard QLabel{color:#95a4ba;padding:4px} #stepCard QLabel:first-child{color:#8d7eff;font-weight:800} #scoreValue{font-size:38px;font-weight:800;color:#60d5a0}
        QWebEngineView{background:white}
        """)


if __name__ == "__main__":
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setApplicationVersion(APP_VERSION); window=MainWindow(); window.show(); sys.exit(app.exec())
