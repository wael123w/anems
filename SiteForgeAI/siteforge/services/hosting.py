from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from siteforge.core.database import Database
from siteforge.core.secure_store import SecureStore


@dataclass(slots=True)
class HostingProfile:
    name: str
    protocol: str
    host: str
    port: int
    username: str
    remote_path: str
    provider: str = "custom"


class HostingProfiles:
    def __init__(self, db: Database, secrets: SecureStore):
        self.db, self.secrets = db, secrets

    def save(self, website_id: int, profile: HostingProfile, secret_payload: dict[str, Any]) -> None:
        key = f"hosting:{website_id}:{profile.name}"
        self.secrets.set(key, {"profile": asdict(profile), "secret": secret_payload})

    def get(self, website_id: int, name: str) -> dict[str, Any] | None:
        return self.secrets.get(f"hosting:{website_id}:{name}")

    def names(self, website_id: int) -> list[str]:
        prefix = f"hosting:{website_id}:"
        # SecureStore intentionally exposes no raw secrets; names can be tracked in DB credentials.
        return [x["label"] for x in self.db.credentials(website_id, "hosting") if x["label"].startswith(prefix)]
