from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from siteforge.providers.ai import AIClient
from siteforge.services.project_tools import RepairFinding, analyze_project, compare_manifests, project_manifest, unified_diff


@dataclass(slots=True)
class RepairProposal:
    findings: list[RepairFinding]
    changed_files: list[str]
    diff: str
    staged_root: Path


class AIRepairService:
    def __init__(self, client: AIClient | None = None):
        self.client = client

    def inspect(self, root: Path) -> list[RepairFinding]:
        return analyze_project(root)

    def propose(self, root: Path, user_instruction: str = "") -> RepairProposal:
        findings = analyze_project(root)
        if not self.client:
            return RepairProposal(findings, [], "", root)
        files = [p for p in root.rglob("*") if p.is_file() and ".siteforge" not in p.parts]
        context = "\n\n".join(f"FILE: {p.relative_to(root)}\n{p.read_text(encoding='utf-8', errors='replace')[:30000]}" for p in files)
        prompt = f"""Analyze this static website and propose repairs. User instruction: {user_instruction or 'Fix critical and warning findings.'}
Return only JSON: {{\"changes\":[{{\"path\":\"relative/path\",\"content\":\"complete file content\"}}],\"summary\":\"...\"}}.
Do not include binary files, secrets, or files outside the project.
{context}"""
        raw = self.client.complete("You are a cautious website repair engineer. Return valid JSON only.", prompt).strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
        payload = json.loads(raw)
        staged = Path(tempfile.mkdtemp(prefix="siteforge-repair-")) / "project"
        import shutil
        shutil.copytree(root, staged, ignore=shutil.ignore_patterns(".siteforge"))
        changed: list[str] = []
        for item in payload.get("changes", []):
            rel = Path(item["path"])
            if rel.is_absolute() or ".." in rel.parts or rel.suffix.lower() not in {".html", ".css", ".js", ".xml", ".txt", ".svg"}:
                continue
            target = staged / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item.get("content", ""), encoding="utf-8")
            changed.append(rel.as_posix())
        diff = unified_diff(staged, root, changed)
        return RepairProposal(findings, changed, diff, staged)

    def apply(self, root: Path, proposal: RepairProposal, selected_files: list[str] | None = None) -> list[str]:
        allowed = set(selected_files or proposal.changed_files)
        applied: list[str] = []
        for rel in proposal.changed_files:
            if rel not in allowed: continue
            source = proposal.staged_root / rel
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            applied.append(rel)
        return applied
