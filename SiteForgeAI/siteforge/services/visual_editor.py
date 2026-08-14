from __future__ import annotations

import html
import re
from pathlib import Path

from siteforge.services.project_tools import VersionStore


class VisualEditor:
    """Deterministic bridge from a selected DOM element to real project files."""

    def __init__(self, root: Path):
        self.root = root
        self.versions = VersionStore(root)

    def edit_text(self, selector: str, text: str, version_message: str = "Visual AI text edit") -> list[str]:
        if not selector or not text.strip(): raise ValueError("Selector and text are required")
        html_path = self.root / "index.html"; content = html_path.read_text(encoding="utf-8"); self.versions.create(version_message)
        tag = selector.strip().lstrip(".").lstrip("#")
        pattern = rf"(<(?:h1|h2|h3|p|a|button|span)\b[^>]*(?:class=[\"'][^\"']*{re.escape(tag)}[^\"']*[\"']|id=[\"']{re.escape(tag)}[\"'])[^>]*>)(.*?)(</(?:h1|h2|h3|p|a|button|span)>)"
        updated, count = re.subn(pattern, lambda m: m.group(1) + html.escape(text) + m.group(3), content, count=1, flags=re.I | re.S)
        if count == 0: raise ValueError(f"Element not found: {selector}")
        html_path.write_text(updated, encoding="utf-8"); return ["index.html"]

    def edit_style(self, selector: str, css_property: str, value: str, version_message: str = "Visual AI style edit") -> list[str]:
        allowed = {"color", "background-color", "font-size", "padding", "border-radius", "text-align", "direction"}
        if css_property not in allowed: raise ValueError("CSS property is not allowed by the safe visual editor")
        css_path = self.root / "style.css"; content = css_path.read_text(encoding="utf-8") if css_path.exists() else ""; self.versions.create(version_message)
        rule = f"\n/* SiteForge visual edit: {selector} */\n{selector} {{ {css_property}: {value}; }}\n"; css_path.write_text(content + rule, encoding="utf-8"); return ["style.css"]

    def remove_element(self, selector: str, version_message: str = "Visual AI remove element") -> list[str]:
        html_path = self.root / "index.html"; content = html_path.read_text(encoding="utf-8"); self.versions.create(version_message)
        key = selector.strip().lstrip(".").lstrip("#")
        pattern = rf"<([a-z0-9]+)\b[^>]*(?:class=[\"'][^\"']*{re.escape(key)}[^\"']*[\"']|id=[\"']{re.escape(key)}[\"'])[^>]*>.*?</\1>"
        updated, count = re.subn(pattern, "", content, count=1, flags=re.I | re.S)
        if count == 0: raise ValueError(f"Element not found: {selector}")
        html_path.write_text(updated, encoding="utf-8"); return ["index.html"]

    def add_image(self, selector: str, url: str, alt: str = "Website image", version_message: str = "Visual AI add image") -> list[str]:
        if not url.strip(): raise ValueError("Image URL is required")
        html_path = self.root / "index.html"; content = html_path.read_text(encoding="utf-8"); self.versions.create(version_message)
        key = selector.strip().lstrip(".").lstrip("#")
        pattern = rf"(<([a-z0-9]+)\b[^>]*(?:class=[\"'][^\"']*{re.escape(key)}[^\"']*[\"']|id=[\"']{re.escape(key)}[\"'])[^>]*>)(.*?)(</\2>)"
        image = f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(alt, quote=True)}">'
        updated, count = re.subn(pattern, lambda m: m.group(1) + m.group(3) + image + m.group(4), content, count=1, flags=re.I | re.S)
        if count == 0: raise ValueError(f"Element not found: {selector}")
        html_path.write_text(updated, encoding="utf-8"); return ["index.html"]
