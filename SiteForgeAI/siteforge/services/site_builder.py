from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

TEMPLATES: dict[str, dict[str, str]] = {
    "business": {"label": "Business", "accent": "#2563eb", "headline": "Build trust. Grow with confidence."},
    "restaurant": {"label": "Restaurant", "accent": "#dc2626", "headline": "Good food, thoughtfully made."},
    "portfolio": {"label": "Portfolio", "accent": "#7c3aed", "headline": "Selected work, made with intent."},
    "agency": {"label": "Agency", "accent": "#0891b2", "headline": "Creative systems for ambitious teams."},
    "saas": {"label": "SaaS", "accent": "#059669", "headline": "Move your workflow forward."},
    "landing": {"label": "Landing Page", "accent": "#ea580c", "headline": "A clearer path from idea to impact."},
    "real-estate": {"label": "Real Estate", "accent": "#0f766e", "headline": "Find a place that feels like yours."},
    "hotel": {"label": "Hotel", "accent": "#b45309", "headline": "Stay somewhere worth remembering."},
    "medical": {"label": "Medical", "accent": "#0369a1", "headline": "Care that puts people first."},
    "construction": {"label": "Construction", "accent": "#475569", "headline": "Built for the way forward."},
}


class SiteBuilder:
    def create(self, root: Path, *, name: str, description: str, template: str = "landing", seo: dict[str, str] | None = None) -> list[Path]:
        data = TEMPLATES.get(template, TEMPLATES["landing"])
        seo = seo or {}
        root.mkdir(parents=True, exist_ok=True)
        (root / "assets").mkdir(exist_ok=True)
        title = seo.get("title", name)
        meta = seo.get("description", description or data["headline"])
        index = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(meta)}">
        <meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(meta)}">
  <meta property="og:type" content="website"><link rel="canonical" href="https://example.com/">
  <link rel="icon" href="assets/favicon.svg"><link rel="stylesheet" href="style.css">
</head>
<body>
<header class="nav"><a class="brand" href="#">{html.escape(name)}</a><nav><a href="#about">About</a><a href="#services">Services</a><a href="#contact">Contact</a></nav></header>
<main><section class="hero"><span class="eyebrow">{data['label']}</span><h1>{data['headline']}</h1><p>{html.escape(meta)}</p><a class="button" href="#contact">Let's talk</a></section>
<section id="about" class="section"><h2>Designed around your goals</h2><p>{html.escape(description or 'A polished digital experience built for your audience.')}</p></section>
<section id="services" class="cards"><article><img src="assets/favicon.svg" alt="{html.escape(name)} brand mark"><h3>Clarity</h3><p>Simple messaging that helps people choose with confidence.</p></article><article><h3>Craft</h3><p>Responsive, accessible details that feel right on every screen.</p></article><article><h3>Momentum</h3><p>A flexible foundation you can evolve as your business grows.</p></article></section>
<section id="contact" class="section contact"><h2>Ready to begin?</h2><p>Tell us what you are building next.</p><a class="button" href="mailto:hello@example.com">hello@example.com</a></section></main>
<footer>© 2026 {html.escape(name)}. Built with SiteForge AI.</footer><script src="script.js"></script></body></html>'''
        css = f''':root {{ font-family: Inter, ui-sans-serif, system-ui, sans-serif; color:#18212f; background:#fbfcfe; --accent:{data['accent']}; }} * {{ box-sizing:border-box }} body {{ margin:0 }} .nav {{ display:flex; justify-content:space-between; align-items:center; padding:24px max(24px,calc((100% - 1120px)/2)); }} .brand {{ font-weight:800;color:#18212f;text-decoration:none }} nav {{ display:flex;gap:24px }} nav a {{ color:#64748b;text-decoration:none }} .hero {{ max-width:1120px;margin:0 auto;padding:120px 24px 150px }} .eyebrow {{ color:var(--accent);font-weight:700;text-transform:uppercase;letter-spacing:.12em;font-size:12px }} h1 {{ font-size:clamp(44px,8vw,92px);line-height:.98;max-width:850px;margin:18px 0 }} h2 {{ font-size:42px;max-width:650px }} p {{ color:#64748b;font-size:18px;line-height:1.7;max-width:680px }} .button {{ display:inline-block;background:var(--accent);color:#fff;padding:14px 22px;border-radius:10px;text-decoration:none;font-weight:700;margin-top:18px }} .section,.cards {{ max-width:1120px;margin:0 auto;padding:90px 24px }} .cards {{ display:grid;grid-template-columns:repeat(3,1fr);gap:18px }} article {{ background:#fff;border:1px solid #e5eaf0;border-radius:18px;padding:28px;box-shadow:0 12px 35px #233a5d0d }} footer {{ max-width:1120px;margin:auto;padding:40px 24px;color:#94a3b8 }} @media(max-width:700px) {{ nav {{ display:none }} .hero {{ padding-top:70px }} .cards {{ grid-template-columns:1fr }} h1 {{ font-size:52px }} }}'''
        js = "document.querySelectorAll('a[href^=\\\"#\\\"]').forEach(a => a.addEventListener('click', e => { const el=document.querySelector(a.getAttribute('href')); if(el){e.preventDefault();el.scrollIntoView({behavior:'smooth'});} }));"
        favicon = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' fill='%s'/><path d='M18 18h28v8H34v20h-8V26H18z' fill='white'/></svg>" % data["accent"]
        files = {"index.html": index, "style.css": css, "script.js": js, "assets/favicon.svg": favicon,
                 "robots.txt": "User-agent: *\nAllow: /\nSitemap: sitemap.xml\n",
                 "sitemap.xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url><loc>https://example.com/</loc></url></urlset>\n"}
        written = []
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(target)
        return written

    def apply_text_edit(self, root: Path, instruction: str) -> list[Path]:
        """Safe deterministic edits for common editor requests; AI adapters can provide patch files."""
        changed: list[Path] = []
        text = instruction.lower()
        if "عنوان" in text or "headline" in text or "hero" in text:
            target = root / "index.html"
            content = target.read_text(encoding="utf-8")
            match = re.search(r"<h1>(.*?)</h1>", content, re.S)
            if match and instruction.strip():
                replacement = html.escape(instruction.split(":", 1)[-1].strip()) if ":" in instruction else match.group(1)
                target.write_text(content[:match.start(1)] + replacement + content[match.end(1):], encoding="utf-8")
                changed.append(target)
        return changed
