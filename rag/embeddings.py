"""API-based embeddings with a provider abstraction (§39–§42).

    embed_text(text)              -> single vector
    embed_documents(documents)    -> (vectors, EmbeddingChoice actually used)

The rest of the app only uses this interface — chunking, vector store,
retrieval, prompts, generation, and UI never touch a provider directly.

Providers (all remote APIs — NEVER local model downloads):
  - 'openrouter' : OpenRouter /embeddings endpoint (same API key as the LLM).
                   Tries the primary model, then the fallback model (§42).

If no embedding provider is reachable, a clear RuntimeError is raised —
the app must NOT silently switch to a different retrieval mechanism (§42).
"""
from __future__ import annotations

import time

import requests

from config.settings import settings
from rag.embedding_selector import EmbeddingChoice, select_embedding_model
from utils.logging import get_logger

log = get_logger(__name__)

# Small batches + retries: the free embedding tier throttles and one giant
# request is more likely to hit a transient failure than several small ones.
BATCH_SIZE = 8
MAX_ATTEMPTS = 3
RETRYABLE_STATUS = (429, 500, 502, 503, 504)


def _sanitize_text(text: str) -> str:
    """Strip NUL/control chars (except newline/tab) that make APIs return 400.

    Also drops lone surrogates (common in PDFs with odd fonts): they are not
    valid Unicode, break JSON hex escapes, and several embedding models
    reject them with HTTP 400.
    """
    t = "".join(ch for ch in (text or "") if ch in "\n\t" or ord(ch) >= 32)
    t = t.encode("utf-8", errors="ignore").decode("utf-8")
    return t.strip()


class EmbeddingProvider:
    """Interface every provider implements."""

    name = "base"

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """Embeddings via the OpenRouter API (no local files, no GPU)."""

    name = "openrouter"

    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise RuntimeError(
                "Embeddings need OPENROUTER_API_KEY. Set it in .env — "
                "the app uses API-based embeddings only (no local downloads)."
            )
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.timeout = settings.openrouter_timeout

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name
        cleaned = [_sanitize_text(t) for t in texts]
        for i, t in enumerate(cleaned):
            if not t:
                raise RuntimeError(
                    f"Chunk {i + 1} is empty after cleaning — nothing to embed. "
                    "The document may contain pages with no real text."
                )
        vectors: list[list[float]] = []
        for start in range(0, len(cleaned), BATCH_SIZE):
            batch = cleaned[start:start + BATCH_SIZE]
            vectors.extend(self._post_batch(batch, model, headers, start))
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(vectors)} for {len(texts)} texts."
            )
        return vectors

    def _post_batch(
        self, batch: list[str], model: str, headers: dict, offset: int
    ) -> list[list[float]]:
        """POST one small batch with retries on transient failures."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json={"model": model, "input": batch},
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_error = RuntimeError(f"Embedding API request failed: {exc}")
                log.warning("Embed batch @%d attempt %d: %s", offset, attempt, last_error)
                time.sleep(2 * attempt)
                continue
            if resp.status_code in RETRYABLE_STATUS:
                last_error = RuntimeError(
                    f"Embedding API transient error {resp.status_code}: "
                    f"{resp.text[:200]}"
                )
                log.warning("Embed batch @%d attempt %d: %s", offset, attempt, last_error)
                time.sleep(2 * attempt)
                continue
            if resp.status_code == 401:
                raise RuntimeError("Invalid OPENROUTER_API_KEY (401). Check your .env.")
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Embedding API error {resp.status_code} "
                    f"(chunks {offset + 1}-{offset + len(batch)}, model '{model}'): "
                    f"{resp.text[:300]}"
                )
            try:
                items = sorted(resp.json()["data"], key=lambda d: d["index"])
                vecs = [list(d["embedding"]) for d in items]
            except (KeyError, ValueError, TypeError) as exc:
                raise RuntimeError(f"Unexpected embedding response: {exc}") from exc
            if len(vecs) != len(batch):
                raise RuntimeError(
                    f"Embedding count mismatch in batch: got {len(vecs)} "
                    f"for {len(batch)} texts."
                )
            return vecs
        raise RuntimeError(
            f"Embedding API unavailable after {MAX_ATTEMPTS} tries "
            f"(chunks {offset + 1}-{offset + len(batch)}). Last error: {last_error}"
        )


_PROVIDERS = {"openrouter": OpenRouterEmbeddingProvider}


def get_provider(name: str | None = None) -> EmbeddingProvider:
    name = (name or settings.embedding_provider).lower()
    if name not in _PROVIDERS:
        raise RuntimeError(
            f"Unknown embedding provider '{name}'. Available: {sorted(_PROVIDERS)}."
        )
    return _PROVIDERS[name]()


def _embed_with_fallback(
    provider: EmbeddingProvider, texts: list[str], choice: EmbeddingChoice
) -> tuple[list[list[float]], EmbeddingChoice]:
    """Try primary model, then the configured fallback model (§42)."""
    candidates = [choice.model]
    if settings.embedding_fallback_model != choice.model:
        candidates.append(settings.embedding_fallback_model)
    last_error: Exception | None = None
    for model in candidates:
        try:
            vectors = provider.embed(texts, model)
            used = EmbeddingChoice(
                provider=choice.provider, model=model,
                dimensions=len(vectors[0]) if vectors else choice.dimensions,
                reason=choice.reason
                + ("" if model == choice.model else f" (primary failed; fell back to '{model}')."),
            )
            return vectors, used
        except Exception as exc:
            log.warning("Embedding model '%s' failed: %s", model, exc)
            last_error = exc
    raise RuntimeError(
        "No embedding provider available. Tried: "
        + ", ".join(candidates)
        + f". Last error: {last_error}"
    )


def embed_documents(
    texts: list[str], model: str | None = None
) -> tuple[list[list[float]], EmbeddingChoice]:
    """Embed a batch; returns (vectors, choice-actually-used).

    `model` pins the exact model (used at query time so the query vector
    always matches the index's dimensions — never silently re-selected).
    """
    if not texts:
        choice = select_embedding_model()
        return [], choice
    if model:
        choice = EmbeddingChoice(
            provider=settings.embedding_provider, model=model,
            dimensions=None, reason=f"Pinned to index model '{model}'.",
        )
    else:
        choice = select_embedding_model()
    provider = get_provider(choice.provider)
    return _embed_with_fallback(provider, texts, choice)


def embed_text(text: str, model: str | None = None) -> list[float]:
    """Embed a single text with the currently selected (or pinned) model."""
    vectors, _ = embed_documents([text], model=model)
    return vectors[0]


def embed_query(query: str, model: str | None = None) -> list[float]:
    """Embed a retrieval query (same model family as the documents)."""
    return embed_text(query, model=model)
