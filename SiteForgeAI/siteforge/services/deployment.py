from __future__ import annotations

import ftplib
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    import paramiko
except ImportError:  # pragma: no cover
    paramiko = None


@dataclass(slots=True)
class Issue:
    severity: str
    message: str
    file: str = ""


def validate_project(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    required = ["index.html", "style.css", "script.js", "robots.txt", "sitemap.xml"]
    for name in required:
        if not (root / name).exists():
            issues.append(Issue("error", f"Missing required file: {name}", name))
    html = root / "index.html"
    if html.exists():
        content = html.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"<title>.*?</title>", content, re.I | re.S): issues.append(Issue("error", "Missing title", "index.html"))
        if not re.search(r'<meta[^>]+name=[\"\']description', content, re.I): issues.append(Issue("warning", "Missing meta description", "index.html"))
        for src in re.findall(r'(?:src|href)=[\"\']([^#][^\"\']+)', content, re.I):
            if not src.startswith(("http://", "https://", "mailto:", "data:", "/")) and not (root / src).exists():
                issues.append(Issue("error", f"Broken local reference: {src}", "index.html"))
    for image in root.rglob("*"):
        if image.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"} and image.name != "favicon.svg":
            if image.suffix.lower() != ".svg":
                issues.append(Issue("warning", "Review image ALT text in HTML", str(image.relative_to(root))))
    return issues


def export_zip(root: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    excluded_names = {".siteforge", ".env", ".env.local", "secrets.bin", "siteforge.db"}
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in root.rglob("*"):
            rel = item.relative_to(root)
            if item.is_file() and not any(part in excluded_names or (part.startswith(".") and part not in {".well-known"}) for part in rel.parts):
                archive.write(item, rel)
    return destination


def deployment_diff(local: Path, remote_manifest: dict[str, str] | None = None) -> dict[str, list[str]]:
    from siteforge.services.project_tools import project_manifest
    current = project_manifest(local)
    remote = remote_manifest or {}
    return {"new": sorted(set(current) - set(remote)), "modified": sorted(path for path in set(current) & set(remote) if current[path] != remote[path]), "deleted": sorted(set(remote) - set(current))}


def backup_project(root: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copytree(root, target)
    return target


class Publisher:
    def publish(self, root: Path, cfg: dict, progress: Callable[[int, str], None], cancel: Callable[[], bool]) -> str:
        protocol = cfg.get("protocol", "sftp").lower()
        if protocol == "sftp": return self._sftp(root, cfg, progress, cancel)
        if protocol == "cpanel": return upload_cpanel(root, cfg, progress, cancel)
        if protocol == "directadmin": return upload_directadmin(root, cfg, progress, cancel)
        return self._ftp(root, cfg, progress, cancel, secure=protocol == "ftps")

    def _sftp(self, root: Path, cfg: dict, progress, cancel) -> str:
        if paramiko is None: raise RuntimeError("paramiko is required for SFTP")
        transport = paramiko.Transport((cfg["host"], int(cfg.get("port", 22))))
        transport.connect(username=cfg["username"], password=cfg.get("password", ""))
        client = paramiko.SFTPClient.from_transport(transport)
        try:
            files = [p for p in root.rglob("*") if p.is_file()]
            for i, path in enumerate(files, 1):
                if cancel(): raise RuntimeError("Deployment cancelled")
                remote = cfg.get("remote_path", "/") + "/" + str(path.relative_to(root)).replace("\\", "/")
                parent = remote.rsplit("/", 1)[0]
                try: client.chdir(parent)
                except IOError: pass
                client.put(str(path), remote)
                progress(int(i / len(files) * 100), path.name)
        finally:
            client.close(); transport.close()
        return f"Uploaded {len(files)} files via SFTP"

    def _ftp(self, root: Path, cfg: dict, progress, cancel, secure: bool) -> str:
        ftp = ftplib.FTP_TLS() if secure else ftplib.FTP()
        ftp.connect(cfg["host"], int(cfg.get("port", 21)), timeout=30); ftp.login(cfg["username"], cfg.get("password", ""))
        if secure: ftp.prot_p()
        files = [p for p in root.rglob("*") if p.is_file() and ".siteforge" not in p.parts]
        base = cfg.get("remote_path", "/").rstrip("/") or "/"
        for i, path in enumerate(files, 1):
            if cancel(): raise RuntimeError("Deployment cancelled")
            rel = str(path.relative_to(root)).replace("\\", "/")
            parts = rel.split("/")
            ftp.cwd(base)
            for folder in parts[:-1]:
                try: ftp.mkd(folder)
                except ftplib.error_perm: pass
                ftp.cwd(folder)
            with path.open("rb") as handle: ftp.storbinary("STOR " + parts[-1], handle)
            progress(int(i / len(files) * 100), rel)
        ftp.quit(); return f"Uploaded {len(files)} files via {'FTPS' if secure else 'FTP'}"


def import_project(source: Path, destination: Path) -> Path:
    """Import a folder or ZIP into a new local project without path traversal."""
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    destination.mkdir(parents=True)
    if source.is_dir():
        for item in source.iterdir():
            target = destination / item.name
            if item.is_dir(): shutil.copytree(item, target)
            else: shutil.copy2(item, target)
        return destination
    if source.suffix.lower() != ".zip":
        raise ValueError("Import source must be a folder or ZIP file")
    with zipfile.ZipFile(source) as archive:
        base = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not str(target).startswith(str(base)):
                raise ValueError("Unsafe ZIP path detected")
        archive.extractall(destination)
    return destination


def upload_cpanel(root: Path, cfg: dict, progress, cancel) -> str:
    """Upload through cPanel Fileman API when the host exposes it."""
    import requests
    url = cfg.get("base_url", "").rstrip("/") + "/execute/Fileman/upload_files"
    headers = {"Authorization": f"cpanel {cfg['username']}:{cfg['api_token']}"}
    files = [p for p in root.rglob("*") if p.is_file()]
    for index, path in enumerate(files, 1):
        if cancel(): raise RuntimeError("Deployment cancelled")
        with path.open("rb") as handle:
            response = requests.post(url, headers=headers, data={"dir": cfg.get("remote_path", "/public_html")}, files={"file": handle}, timeout=60)
        if not response.ok: raise RuntimeError(f"cPanel upload failed: {response.text[:300]}")
        progress(int(index / len(files) * 100), path.name)
    return f"Uploaded {len(files)} files via cPanel API"


def upload_directadmin(root: Path, cfg: dict, progress, cancel) -> str:
    """Upload through DirectAdmin API when the host exposes it."""
    import requests
    url = cfg.get("base_url", "").rstrip("/") + "/CMD_API_FILE_MANAGER"
    auth = (cfg["username"], cfg.get("password", ""))
    files = [p for p in root.rglob("*") if p.is_file()]
    for index, path in enumerate(files, 1):
        if cancel(): raise RuntimeError("Deployment cancelled")
        with path.open("rb") as handle:
            response = requests.post(url, auth=auth, data={"action":"upload","path":cfg.get("remote_path","/public_html"),"filename":path.name}, files={"file":handle}, timeout=60)
        if not response.ok: raise RuntimeError(f"DirectAdmin upload failed: {response.text[:300]}")
        progress(int(index / len(files) * 100), path.name)
    return f"Uploaded {len(files)} files via DirectAdmin API"
