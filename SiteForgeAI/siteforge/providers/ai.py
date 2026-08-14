from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class AIConfig:
    provider: str
    api_key: str
    model: str
    base_url: str = ""


class AIError(RuntimeError):
    pass


class AIClient:
    def __init__(self, config: AIConfig):
        self.config = config

    def complete(self, system: str, user: str) -> str:
        p = self.config.provider.lower()
        if p in {"openai", "openrouter"}:
            url = self.config.base_url or ("https://openrouter.ai/api/v1/chat/completions" if p == "openrouter" else "https://api.openai.com/v1/chat/completions")
            headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
            r = requests.post(url, headers=headers, json={"model": self.config.model, "messages": [{"role":"system","content":system},{"role":"user","content":user}]}, timeout=120)
            if not r.ok: raise AIError(f"{r.status_code}: {r.text[:300]}")
            return r.json()["choices"][0]["message"]["content"]
        if p == "gemini":
            url = self.config.base_url or f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model}:generateContent"
            r = requests.post(url, params={"key": self.config.api_key}, json={"contents":[{"parts":[{"text": system + "\\n" + user}]}]}, timeout=120)
            if not r.ok: raise AIError(f"{r.status_code}: {r.text[:300]}")
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        if p == "claude":
            url = self.config.base_url or "https://api.anthropic.com/v1/messages"
            r = requests.post(url, headers={"x-api-key":self.config.api_key,"anthropic-version":"2023-06-01","content-type":"application/json"}, json={"model":self.config.model,"max_tokens":8192,"system":system,"messages":[{"role":"user","content":user}]}, timeout=120)
            if not r.ok: raise AIError(f"{r.status_code}: {r.text[:300]}")
            return r.json()["content"][0]["text"]
        raise AIError(f"مزود غير مدعوم: {self.config.provider}")

    def generate_site_spec(self, brief: str) -> dict[str, Any]:
        system = "Return only valid JSON with keys: name, description, template, seo, files. files is an array of {path, content}. Create a complete static website."
        raw = self.complete(system, brief)
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)
