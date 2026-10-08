"""Small pure-Python helpers (no semantic logic here)."""
from __future__ import annotations

import re
import uuid


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def safe_truncate(text: str, limit: int = 4000) -> str:
    """Truncate long text for LLM prompts without breaking mid-word badly."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit - 200:
        cut = cut[:space]
    return cut + "\n...[truncated]..."


def clean_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split())
