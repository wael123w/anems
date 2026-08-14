from pathlib import Path
import zipfile

from siteforge.core.secure_store import SecureStore
from siteforge.services.deployment import deployment_diff, export_zip, import_project
from siteforge.services.project_tools import VersionStore, analyze_project, project_manifest
from siteforge.services.site_builder import SiteBuilder


def test_import_zip_and_reject_traversal(tmp_path: Path):
    source = tmp_path / "source"
    SiteBuilder().create(source, name="Import", description="demo")
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for item in source.rglob("*"):
            if item.is_file(): z.write(item, item.relative_to(source))
    imported = import_project(archive, tmp_path / "imported")
    assert (imported / "index.html").exists()

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as z: z.writestr("../escape.txt", "bad")
    try: import_project(unsafe, tmp_path / "unsafe-dest")
    except ValueError: pass
    else: raise AssertionError("unsafe ZIP should be rejected")


def test_manifest_diff_and_versions(tmp_path: Path):
    root = tmp_path / "site"
    SiteBuilder().create(root, name="Versioned", description="demo")
    before = project_manifest(root)
    version = VersionStore(root).create("Initial version")
    (root / "index.html").write_text("changed", encoding="utf-8")
    after = project_manifest(root)
    diff = deployment_diff(root, before)
    assert "index.html" in diff["modified"]
    VersionStore(root).restore(version.name)
    assert project_manifest(root) == before


def test_repair_analysis_and_secret_storage(tmp_path: Path):
    root = tmp_path / "broken"
    root.mkdir(); (root / "index.html").write_text("<html><body><img src='missing.png'></body></html>", encoding="utf-8")
    findings = analyze_project(root)
    assert any(f.category == "SEO" for f in findings)
    store = SecureStore(tmp_path / "secrets.bin", passphrase="test")
    store.set("hosting", {"password": "dont-log-me"})
    assert store.get("hosting")["password"] == "dont-log-me"
    assert b"dont-log-me" not in (tmp_path / "secrets.bin").read_bytes()


def test_export_excludes_internal_files(tmp_path: Path):
    root = tmp_path / "site"; SiteBuilder().create(root, name="Export", description="demo")
    (root / ".env").write_text("API_KEY=secret", encoding="utf-8")
    (root / ".siteforge").mkdir(); (root / ".siteforge" / "version.json").write_text("{}")
    archive = export_zip(root, tmp_path / "safe.zip")
    with zipfile.ZipFile(archive) as z:
        names = set(z.namelist())
    assert ".env" not in names and not any(name.startswith(".siteforge/") for name in names)
