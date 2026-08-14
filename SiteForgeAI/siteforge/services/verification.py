from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests


@dataclass(slots=True)
class VerificationResult:
    ok: bool
    status_code: int | None
    message: str
    missing_local_files: list[str]


def verify_deployment(root: Path, base_url: str | None = None, timeout: int = 20) -> VerificationResult:
    missing = [name for name in ("index.html", "robots.txt", "sitemap.xml") if not (root / name).exists()]
    status = None
    if base_url:
        try:
            response = requests.get(urljoin(base_url.rstrip("/") + "/", "index.html"), timeout=timeout, allow_redirects=True)
            status = response.status_code
            if response.status_code >= 400:
                return VerificationResult(False, status, f"HTTP verification failed with {response.status_code}", missing)
        except requests.RequestException as exc:
            return VerificationResult(False, None, f"HTTP verification unavailable: {exc}", missing)
    ok = not missing
    return VerificationResult(ok, status, "Deployment verified" if ok else "Required local files are missing", missing)
