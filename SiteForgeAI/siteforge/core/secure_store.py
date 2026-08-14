from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import platform
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class SecureStore:
    """Encrypted local storage for BYOK and hosting credentials.

    The encryption key is derived from a machine-bound seed and an optional
    user passphrase. The application never ships provider or hosting secrets.
    """

    def __init__(self, path: Path, passphrase: str | None = None):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        machine_seed = f"{platform.node()}::{getpass.getuser()}::siteforge-ai".encode()
        salt = hashlib.sha256(machine_seed).digest()[:16]
        secret = machine_seed + (passphrase or os.environ.get("SITEFORGE_MASTER_PASSWORD", "")).encode()
        key = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", secret, salt, 210_000, 32))
        self._fernet = Fernet(key)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self._fernet.decrypt(self.path.read_bytes()))
        except (InvalidToken, ValueError, json.JSONDecodeError):
            raise RuntimeError("تعذر فك مخزن الأسرار. تحقق من كلمة المرور الرئيسية.")

    def _write(self, data: dict[str, Any]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_bytes(self._fernet.encrypt(json.dumps(data).encode()))
        temp.replace(self.path)

    def set(self, key: str, value: dict[str, Any]) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def get(self, key: str) -> dict[str, Any] | None:
        return self._read().get(key)

    def delete(self, key: str) -> None:
        data = self._read()
        data.pop(key, None)
        self._write(data)
