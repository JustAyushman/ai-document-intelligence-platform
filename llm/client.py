"""Reusable OpenRouter LLM client.

All other modules call this — nobody repeats API connection code.
The model is chosen by llm/model_selector.py (automatic) and passed
per-call; the client only falls back to a default when no model is given.
If no API key is configured, `available` is False and callers use
graceful fallbacks so document processing still runs offline.
"""
from __future__ import annotations

import json

import requests

from config.settings import settings
from utils.logging import get_logger

log = get_logger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.timeout = settings.openrouter_timeout
        self.last_model_used: str = ""

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        model: str | None = None,
    ) -> str:
        """Return assistant message content (raises on failure).

        `model` comes from llm/model_selector.select_llm(); when None,
        the selector's default is used — never a hard-coded id here.
        """
        if not self.available:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")
        from llm.model_selector import default_model

        model = model or default_model()
        self.last_model_used = model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name
        payload: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers, json=payload, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
        if resp.status_code == 401:
            raise RuntimeError("Invalid OpenRouter API key (401). Check your .env.")
        if resp.status_code == 429:
            raise RuntimeError("OpenRouter rate limit hit (429). Try again shortly.")
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:500]}")
        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response: {exc}") from exc


# Shared singleton — import this everywhere.
client = LLMClient()
