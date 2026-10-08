"""Retriever: semantic search + light metadata filtering/reranking."""
from __future__ import annotations

import re

from config.settings import settings
from models.schemas import Chunk, RequirementSpec, RetrievedChunk
from rag import embeddings
from rag.vector_store import VectorStore


def retrieve(
    query: str | RequirementSpec,
    store: VectorStore,
    document_id: str,
    top_k: int | None = None,
    metadata_filter: dict | None = None,
) -> list[RetrievedChunk]:
    """Semantic retrieval scoped to one document, with optional metadata filter."""
    top_k = top_k or settings.top_k
    if isinstance(query, RequirementSpec):
        query_text = query.rewritten_query or query.target
    else:
        query_text = query
    if len(store) == 0:
        return []

    # Pin the query to the index's own embedding model: after a fallback,
    # the index dims may differ from the currently-selected model, and a
    # re-selected model would produce an incompatible query vector.
    index_model = None
    if getattr(store, "embedding_id", None) and ":" in store.embedding_id:
        index_model = store.embedding_id.split(":", 1)[1]
    qvec = embeddings.embed_query(query_text, model=index_model)
    if store.dimensions and len(qvec) != store.dimensions:
        raise RuntimeError(
            f"Query embedding dim ({len(qvec)}) != index dim ({store.dimensions}). "
            "The embedding model changed — re-index the document."
        )
    hits = store.search(qvec, top_k=top_k * 2, document_id=document_id)

    results = [RetrievedChunk(chunk=c, score=s) for c, s in hits]
    if metadata_filter:
        results = _apply_metadata_filter(results, metadata_filter)
    results = _rerank(query_text, results)
    return results[:top_k]


def _apply_metadata_filter(
    results: list[RetrievedChunk], metadata_filter: dict
) -> list[RetrievedChunk]:
    """Keep chunks matching e.g. {'section': 'B', 'year': 2024} (substring match)."""
    if not metadata_filter:
        return results
    kept: list[RetrievedChunk] = []
    for rc in results:
        c: Chunk = rc.chunk
        ok = True
        for key, val in metadata_filter.items():
            hay = str(getattr(c, key, "") or c.extra.get(key, ""))
            if str(val).lower() not in hay.lower() and str(val).lower() not in c.text.lower():
                ok = False
                break
        if ok:
            kept.append(rc)
    return kept or results  # never return empty if filter was too strict


def _rerank(query: str, results: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Small keyword-overlap boost on top of vector scores (transparent)."""
    qtokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    qtokens = {t for t in qtokens if len(t) > 2}
    if not qtokens:
        return results
    rescored = []
    for rc in results:
        ctokens = set(re.findall(r"[a-z0-9]+", rc.chunk.text.lower()))
        overlap = len(qtokens & ctokens) / max(len(qtokens), 1)
        rescored.append(RetrievedChunk(chunk=rc.chunk, score=rc.score + 0.15 * overlap))
    rescored.sort(key=lambda r: r.score, reverse=True)
    return rescored
