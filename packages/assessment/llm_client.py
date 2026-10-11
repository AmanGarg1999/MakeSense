"""OpenAI-compatible scoring model client (LL-05 default verifier).

Env-configured, stdlib-only HTTP (no SDK dependency):
  ASSESS_LLM_BASE_URL  default http://100.72.85.102:18300/v1  (DGX Spark vLLM)
  ASSESS_LLM_MODEL     default qwen3.8-flash-next
  ASSESS_LLM_API_KEY   optional bearer token
  ASSESS_LLM_TIMEOUT   default 120 (s)
"""
from __future__ import annotations

import json
import os
import urllib.request


class OpenAICompatClient:
    def __init__(self, base_url: str | None = None, model: str | None = None,
                 api_key: str | None = None, timeout: int | None = None,
                 temperature: float = 0.0):
        self.base_url = (base_url or os.environ.get(
            "ASSESS_LLM_BASE_URL", "http://100.72.85.102:18300/v1")).rstrip("/")
        self.model_name = model or os.environ.get("ASSESS_LLM_MODEL", "qwen3.8-flash-next")
        self.api_key = api_key if api_key is not None else os.environ.get("ASSESS_LLM_API_KEY")
        self.timeout = timeout or int(os.environ.get("ASSESS_LLM_TIMEOUT", "120"))
        self.temperature = temperature

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model_name,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode())
        return body["choices"][0]["message"]["content"]
