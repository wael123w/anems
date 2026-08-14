from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from siteforge.providers.ai import AIClient
from siteforge.services.site_builder import SiteBuilder


class AIGenerationService:
    def __init__(self, client: AIClient | None):
        self.client = client

    def plan(self, brief: str) -> dict[str, Any]:
        if not brief.strip(): raise ValueError("Website brief is required")
        if not self.client:
            return {"name": "SiteForge Website", "description": brief, "template": "landing", "seo": {"title": "SiteForge Website", "description": brief}, "files": []}
        return self.client.generate_site_spec(
            "Create a practical static website plan first. Include pages, sections, content, design system, SEO and complete file contents. The result must be editable HTML/CSS/JS with no external backend."
            + "\nUSER BRIEF:\n" + brief
        )

    def generate(self, root: Path, brief: str) -> dict[str, Any]:
        spec = self.plan(brief)
        root.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        for item in spec.get("files", []):
            rel = Path(str(item.get("path", "")))
            if rel.is_absolute() or ".." in rel.parts or rel.name in {"secrets.bin", ".env", "siteforge.db"}:
                continue
            if rel.suffix.lower() not in {".html", ".css", ".js", ".svg", ".xml", ".txt", ".json"}:
                continue
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(item.get("content", "")), encoding="utf-8")
            written.append(rel.as_posix())
        if not (root / "index.html").exists():
            builder = SiteBuilder()
            builder.create(root, name=str(spec.get("name", "SiteForge Website")), description=str(spec.get("description", brief)), template=str(spec.get("template", "landing")), seo=spec.get("seo") or {})
            written = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
        return {"spec": spec, "files": written}
