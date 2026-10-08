"""Centralized application configuration.

All tunable values live here. Secrets come from environment / .env.
Nothing else in the codebase should hard-code these values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _getenv(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _getint(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _getfloat(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _getbool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    """Single source of truth for configuration."""

    # --- OpenRouter ---
    openrouter_api_key: str = field(default_factory=lambda: _getenv("OPENROUTER_API_KEY"))
    openrouter_model: str = field(
        default_factory=lambda: _getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    )
    openrouter_base_url: str = field(
        default_factory=lambda: _getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
    )
    openrouter_timeout: int = field(default_factory=lambda: _getint("OPENROUTER_TIMEOUT", 60))
    openrouter_site_url: str = field(default_factory=lambda: _getenv("OPENROUTER_SITE_URL", ""))
    openrouter_app_name: str = field(
        default_factory=lambda: _getenv("OPENROUTER_APP_NAME", "doc-intelligence-platform")
    )

    # --- Model selection ---
    # AUTO_SELECT_MODELS=true (default): selectors pick LLM + embeddings.
    # Set false + OPENROUTER_MODEL / EMBEDDING_MODEL for developer override.
    auto_select_models: bool = field(default_factory=lambda: _getbool("AUTO_SELECT_MODELS", True))
    # Optional developer overrides (honored when auto-select is off,
    # or as preferred defaults when on).
    openrouter_model: str = field(
        default_factory=lambda: _getenv("OPENROUTER_MODEL", "")
    )
    llm_efficient: str = field(
        default_factory=lambda: _getenv("LLM_EFFICIENT_MODEL", "openai/gpt-4o-mini")
    )
    llm_general: str = field(
        default_factory=lambda: _getenv("LLM_GENERAL_MODEL", "openai/gpt-4o-mini")
    )
    llm_reasoning: str = field(
        default_factory=lambda: _getenv(
            "LLM_REASONING_MODEL", "openai/gpt-4o"
        )
    )
    large_doc_chars: int = field(default_factory=lambda: _getint("LARGE_DOC_CHARS", 60000))

    # --- RAG ---
    # API-based embeddings only — no local model downloads (Streamlit-friendly).
    embedding_provider: str = field(
        default_factory=lambda: _getenv("EMBEDDING_PROVIDER", "openrouter")
    )
    embedding_model: str = field(
        default_factory=lambda: _getenv("EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b:free")
    )
    embedding_fallback_model: str = field(
        default_factory=lambda: _getenv(
            "EMBEDDING_FALLBACK_MODEL", "openai/text-embedding-3-small"
        )
    )
    chunk_size: int = field(default_factory=lambda: _getint("CHUNK_SIZE", 800))
    chunk_overlap: int = field(default_factory=lambda: _getint("CHUNK_OVERLAP", 120))
    top_k: int = field(default_factory=lambda: _getint("TOP_K", 5))
    max_retries: int = field(default_factory=lambda: _getint("MAX_RETRIES", 3))

    # --- App ---
    max_upload_mb: int = field(default_factory=lambda: _getint("MAX_UPLOAD_MB", 25))
    supported_extensions: tuple = (".pdf", ".docx", ".doc", ".txt", ".md")

    @property
    def llm_configured(self) -> bool:
        return bool(self.openrouter_api_key)


settings = Settings()
