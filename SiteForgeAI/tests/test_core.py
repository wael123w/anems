from pathlib import Path

from siteforge.core.database import Database
from siteforge.services.deployment import export_zip, validate_project
from siteforge.services.site_builder import SiteBuilder


def test_site_builder_creates_real_files(tmp_path: Path):
    root = tmp_path / "site"
    files = SiteBuilder().create(root, name="Test Site", description="A test site", template="business")
    names = {p.relative_to(root).as_posix() for p in files}
    assert {"index.html", "style.css", "script.js", "robots.txt", "sitemap.xml", "assets/favicon.svg"} <= names
    assert "<title>Test Site</title>" in (root / "index.html").read_text()


def test_database_persists_websites(tmp_path: Path):
    db = Database(tmp_path / "siteforge.db")
    site = db.create_website("Demo", "desc", str(tmp_path / "demo"), "landing")
    assert db.list_websites()[0].id == site.id


def test_validation_and_zip(tmp_path: Path):
    root = tmp_path / "site"
    SiteBuilder().create(root, name="Demo", description="desc")
    assert not [i for i in validate_project(root) if i.severity == "error"]
    archive = export_zip(root, tmp_path / "demo.zip")
    assert archive.exists() and archive.stat().st_size > 0
