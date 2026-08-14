from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class FileChange:
    path: str
    kind: str
    before_hash: str = ""
    after_hash: str = ""


@dataclass(slots=True)
class RepairFinding:
    category: str
    severity: str
    problem: str
    explanation: str
    proposed_fix: str
    file: str


def iter_project_files(root: Path) -> list[Path]:
    excluded = {".git", ".siteforge", "__pycache__"}
    return sorted(p for p in root.rglob("*") if p.is_file() and not any(part in excluded for part in p.parts))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_manifest(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)).replace("\\", "/"): file_hash(p) for p in iter_project_files(root)}


def compare_manifests(before: dict[str, str], after: dict[str, str]) -> list[FileChange]:
    changes: list[FileChange] = []
    for path in sorted(set(before) | set(after)):
        if path not in before:
            changes.append(FileChange(path, "new", "", after[path]))
        elif path not in after:
            changes.append(FileChange(path, "deleted", before[path], ""))
        elif before[path] != after[path]:
            changes.append(FileChange(path, "modified", before[path], after[path]))
    return changes


def unified_diff(root: Path, before_root: Path, paths: Iterable[str]) -> str:
    blocks: list[str] = []
    for rel in paths:
        before = before_root / rel
        after = root / rel
        old = before.read_text(encoding="utf-8", errors="replace").splitlines(True) if before.exists() else []
        new = after.read_text(encoding="utf-8", errors="replace").splitlines(True) if after.exists() else []
        blocks.extend(difflib.unified_diff(old, new, fromfile=f"before/{rel}", tofile=f"after/{rel}"))
    return "".join(blocks)


def analyze_project(root: Path) -> list[RepairFinding]:
    findings: list[RepairFinding] = []
    html_file = root / "index.html"
    if not html_file.exists():
        findings.append(RepairFinding("HTML", "critical", "Missing entry page", "No index.html was found.", "Create an index.html entry page.", "index.html"))
        return findings
    content = html_file.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"<title>.*?</title>", content, re.I | re.S):
        findings.append(RepairFinding("SEO", "critical", "Missing title", "Search engines and browser tabs have no title.", "Add a descriptive title element.", "index.html"))
    if not re.search(r'<meta[^>]+name=["\']description', content, re.I):
        findings.append(RepairFinding("SEO", "warning", "Missing meta description", "The page lacks a search snippet description.", "Add a meta description based on the project brief.", "index.html"))
    refs = re.findall(r'(?:src|href)=["\']([^#][^"\']+)', content, re.I)
    for ref in refs:
        if ref.startswith(("http://", "https://", "mailto:", "data:", "/")):
            continue
        if not (root / ref).exists():
            findings.append(RepairFinding("Links", "critical", f"Missing asset: {ref}", "A local href or src points to a file that does not exist.", "Create the file or update the reference.", "index.html"))
    for image in re.findall(r"<img\b([^>]*)>", content, re.I | re.S):
        if not re.search(r"\balt=[\"']", image, re.I):
            findings.append(RepairFinding("SEO", "warning", "Image missing ALT text", "Images without ALT text reduce accessibility and SEO quality.", "Add descriptive ALT text.", "index.html"))
    css = root / "style.css"
    if css.exists() and "@media" not in css.read_text(encoding="utf-8", errors="replace"):
        findings.append(RepairFinding("Responsive", "warning", "No responsive media query", "The stylesheet has no visible responsive breakpoint.", "Add mobile and tablet layout rules.", "style.css"))
    js = root / "script.js"
    if js.exists() and "console.error" in js.read_text(encoding="utf-8", errors="replace"):
        findings.append(RepairFinding("JavaScript", "warning", "Console error found", "The JavaScript file contains an explicit console error.", "Inspect and handle the failing branch.", "script.js"))
    return findings


class VersionStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.root = project_root / ".siteforge" / "versions"
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, message: str) -> Path:
        version_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        target = self.root / version_id
        shutil.copytree(self.project_root, target, ignore=shutil.ignore_patterns(".siteforge"))
        metadata = {"id": version_id, "message": message, "created_at": datetime.now(timezone.utc).isoformat(), "manifest": project_manifest(target)}
        (target / "version.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return target

    def list(self) -> list[dict]:
        records = []
        for folder in sorted(self.root.iterdir(), reverse=True):
            metadata = folder / "version.json"
            if metadata.exists(): records.append(json.loads(metadata.read_text(encoding="utf-8")))
        return records

    def restore(self, version_id: str) -> None:
        source = self.root / version_id
        if not source.exists(): raise FileNotFoundError(version_id)
        for item in self.project_root.iterdir():
            if item.name != ".siteforge":
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        for item in source.iterdir():
            if item.name != "version.json":
                destination = self.project_root / item.name
                shutil.copytree(item, destination) if item.is_dir() else shutil.copy2(item, destination)
