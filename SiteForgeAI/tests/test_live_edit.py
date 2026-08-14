from pathlib import Path

from siteforge.services.site_builder import SiteBuilder
from siteforge.services.visual_editor import VisualEditor


def test_live_text_edit_writes_real_html_and_backup(tmp_path: Path):
    root = tmp_path / "site"
    SiteBuilder().create(root, name="Live", description="demo")
    changed = VisualEditor(root).edit_text(".brand", "New Brand")
    assert changed == ["index.html"]
    assert "New Brand" in (root / "index.html").read_text(encoding="utf-8")
    assert list((root / ".siteforge" / "versions").iterdir())


def test_live_style_edit_writes_real_css(tmp_path: Path):
    root = tmp_path / "site"
    SiteBuilder().create(root, name="Live", description="demo")
    changed = VisualEditor(root).edit_style(".button", "background-color", "#2563eb")
    assert changed == ["style.css"]
    assert "background-color: #2563eb" in (root / "style.css").read_text(encoding="utf-8")


def test_live_delete_and_add_image_write_real_html(tmp_path: Path):
    root = tmp_path / "site"
    SiteBuilder().create(root, name="Live", description="demo")
    VisualEditor(root).add_image(".section", "assets/hero.png", "Hero image")
    assert "assets/hero.png" in (root / "index.html").read_text(encoding="utf-8")
    VisualEditor(root).remove_element(".contact")
    assert "id=\"contact\"" not in (root / "index.html").read_text(encoding="utf-8")
