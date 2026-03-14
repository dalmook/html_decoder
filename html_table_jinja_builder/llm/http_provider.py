from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from llm.base_provider import BaseLLMProvider


class HttpLLMProvider(BaseLLMProvider):
    """Simple HTTP Chat Completions provider (OpenAI-compatible payload style)."""

    def __init__(self, provider_cfg: dict[str, Any]) -> None:
        self.base_url = provider_cfg.get("base_url", "")
        self.api_key_env = provider_cfg.get("api_key_env", "LLM_API_KEY")
        self.model = provider_cfg.get("model", "")
        self.timeout_sec = int(provider_cfg.get("timeout_sec", 120))
        self.temperature = float(provider_cfg.get("temperature", 0.1))
        self.max_tokens = int(provider_cfg.get("max_tokens", 4000))

    def generate(self, prompt: str) -> str:
        if not self.base_url:
            raise RuntimeError("provider.base_url is empty")

        api_key = os.getenv(self.api_key_env, "")
        if not api_key:
            raise RuntimeError(f"Missing API key env: {self.api_key_env}")

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": "You are an Oracle SQL drafting assistant."},
                {"role": "user", "content": prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        req = urllib.request.Request(self.base_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                txt = resp.read().decode("utf-8")
                parsed = json.loads(txt)
                choices = parsed.get("choices", [])
                if not choices:
                    raise RuntimeError("LLM response has no choices")
                return choices[0].get("message", {}).get("content", "")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM HTTP error {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM URL error: {exc}") from exc
