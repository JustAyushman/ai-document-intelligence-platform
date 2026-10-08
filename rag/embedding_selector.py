"""Centralized automatic embedding-model selection (the ONLY place that picks one).

Rules (simple, §40):
  1. Developer override: if AUTO_SELECT_MODELS=false and EMBEDDING_MODEL
     is set, use it.
  2. Otherwise pick the configured API provider's primary model.
     (Heuristic hooks — e.g. doc size / language — live here so they
     stay in one place as requirements grow.)

The selector also guards compatibility (§43): every choice carries its
expected vector dimensions, and the pipeline tags each index with the
embedding id so vectors from different models are never mixed.
"""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings

# Known embedding dimensions (used for the vector-store compatibility check).
KNOWN_DIMENSIONS = {
    "nvidia/nemotron-3-embed-1b:free": 2048,
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002": 1536,
}


@dataclass
class DocStats:
    chars: int = 0
    pages: int = 0
    chunk_count: int = 0
    language_hint: str = ""


@dataclass
class EmbeddingChoice:
    provider: str  # e.g. 'openrouter'
    model: str
    dimensions: int | None  # None = discover from first response
    reason: str

    @property
    def embedding_id(self) -> str:
        return f"{self.provider}:{self.model}"


def select_embedding_model(stats: DocStats | None = None) -> EmbeddingChoice:
    """Return the embedding provider/model to use for this task."""
    stats = stats or DocStats()
    if not settings.auto_select_models and settings.embedding_model:
        model = settings.embedding_model
        return EmbeddingChoice(
            provider=settings.embedding_provider,
            model=model,
            dimensions=KNOWN_DIMENSIONS.get(model),
            reason="Developer override (AUTO_SELECT_MODELS=false, EMBEDDING_MODEL set).",
        )
    model = settings.embedding_model
    return EmbeddingChoice(
        provider=settings.embedding_provider,
        model=model,
        dimensions=KNOWN_DIMENSIONS.get(model),
        reason=(
            f"Automatically selected '{model}' via '{settings.embedding_provider}' "
            f"for semantic document retrieval ({stats.chunk_count} chunks)."
        ),
    )
