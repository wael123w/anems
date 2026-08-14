from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Website:
    id: int
    name: str
    description: str
    project_path: str
    template: str
    created_at: str
    updated_at: str


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                project_path TEXT NOT NULL UNIQUE,
                template TEXT NOT NULL DEFAULT 'landing',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                label TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(website_id) REFERENCES websites(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                remote_path TEXT NOT NULL DEFAULT '',
                backup_path TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(website_id) REFERENCES websites(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_websites(self) -> list[Website]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM websites ORDER BY updated_at DESC").fetchall()
        return [Website(**dict(row)) for row in rows]

    def create_website(self, name: str, description: str, project_path: str, template: str) -> Website:
        timestamp = self.now()
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO websites(name,description,project_path,template,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (name, description, project_path, template, timestamp, timestamp),
            )
            website_id = cur.lastrowid
        return Website(website_id, name, description, project_path, template, timestamp, timestamp)

    def touch(self, website_id: int) -> None:
        with self._connect() as db:
            db.execute("UPDATE websites SET updated_at=? WHERE id=?", (self.now(), website_id))

    def save_credential(self, website_id: int, kind: str, label: str, payload: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO credentials(website_id,kind,label,payload,created_at) VALUES(?,?,?,?,?)",
                (website_id, kind, label, json.dumps(payload), self.now()),
            )

    def credentials(self, website_id: int, kind: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM credentials WHERE website_id=?"
        args: list[Any] = [website_id]
        if kind:
            query += " AND kind=?"
            args.append(kind)
        with self._connect() as db:
            rows = db.execute(query, args).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def record_deployment(self, website_id: int, provider: str, status: str, remote_path: str, backup_path: str, message: str) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO deployments(website_id,provider,status,remote_path,backup_path,message,created_at) VALUES(?,?,?,?,?,?,?)",
                (website_id, provider, status, remote_path, backup_path, message, self.now()),
            )

    def deployments(self, website_id: int) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM deployments WHERE website_id=? ORDER BY id DESC", (website_id,))]

    def setting(self, key: str, default: str = "") -> str:
        with self._connect() as db:
            row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
