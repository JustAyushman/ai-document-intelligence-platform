"""Centralized automatic LLM selection (the ONLY place that picks a chat model).

How it works (deliberately simple — §35/36):
  1. Developer override: if AUTO_SELECT_MODELS=false and OPENROUTER_MODEL
     is set, use it (debugging only).
  2. Otherwise pick a tier from the task:
       simple / cheap task  -> efficient model
       standard task         -> general-purpose model
       complex / large task  -> stronger reasoning / large-context model
  3. Optionally verify the pick against OpenRouter's live model list
     (best-effort discovery; never fails the pipeline).

Callers never hard-code model names — they call select_llm(...).
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

from config.settings import settings
from utils.logging import get_logger

log = get_logger(__name__)

# Intents that are usually cheap pattern-matching, not deep reasoning.
SIMPLE_INTENTS = {"classify", "retrieve"}
# Intents that usually need stronger reasoning over multiple chunks.
COMPLEX_INTENTS = {"generate", "custom"}

_model_list_cache: list[str] | None = None


@dataclass
class TaskContext:
    """Everything the selector needs — no raw document text required."""

    intent: str = "custom"
    doc_chars: int = 0
    doc_pages: int = 0
    chunk_count: int = 0
    needs_reasoning: bool = False


@dataclass
class ModelChoice:
    model: str
    tier: str  # efficient | general | reasoning | override
    reason: str


def select_llm(ctx: TaskContext | None = None) -> ModelChoice:
    """Return the OpenRouter model id to use for this task."""
    ctx = ctx or TaskContext()

    # 1. Developer override (advanced, not normal usage).
    if not settings.auto_select_models and settings.openrouter_model:
        return ModelChoice(
            model=settings.openrouter_model,
            tier="override",
            reason="Developer override (AUTO_SELECT_MODELS=false, OPENROUTER_MODEL set).",
        )

    # 2. Automatic tier selection.
    is_large = ctx.doc_chars >= settings.large_doc_chars or ctx.chunk_count > 60
    if ctx.intent in SIMPLE_INTENTS and not is_large and not ctx.needs_reasoning:
        return ModelChoice(
            model=settings.llm_efficient, tier="efficient",
            reason=f"Simple '{ctx.intent}' task on a small document — efficient model.",
        )
    if ctx.intent in COMPLEX_INTENTS or ctx.needs_reasoning or is_large:
        return ModelChoice(
            model=settings.llm_reasoning, tier="reasoning",
            reason=(
                f"Complex '{ctx.intent}' task"
                + (" + large document" if is_large else "")
                + (" + reasoning required" if ctx.needs_reasoning else "")
                + " — stronger model."
            ),
        )
    return ModelChoice(
        model=settings.llm_general, tier="general",
        reason=f"Standard '{ctx.intent}' task — general-purpose model.",
    )


def default_model() -> str:
    """Best single default when no task context exists yet (e.g. startup)."""
    if not settings.auto_select_models and settings.openrouter_model:
        return settings.openrouter_model
    return settings.llm_general


def list_available_models(limit: int = 50) -> list[str]:
    """Best-effort OpenRouter model discovery (cached, never raises)."""
    global _model_list_cache
    if _model_list_cache is not None:
        return _model_list_cache[:limit]
    if not settings.openrouter_api_key:
        return []
    try:
        resp = requests.get(
            f"{settings.openrouter_base_url.rstrip('/')}/models", timeout=15
        )
        if resp.status_code == 200:
            _model_list_cache = [m.get("id", "") for m in resp.json().get("data", [])]
            return _model_list_cache[:limit]
    except Exception as exc:
        log.warning("OpenRouter model discovery failed: %s", exc)
    return []
