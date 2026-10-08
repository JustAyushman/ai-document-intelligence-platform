"""In-memory vector store with document/session isolation.

Each record carries its document_id; retrieval always filters by the
active document_id, so Document A can never leak into Document B.
Swap this class for Chroma/FAISS later without touching callers.
"""
from __future__ import annotations

import math

from models.schemas import Chunk


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n])) or 1.0
    nb = math.sqrt(sum(x * x for x in b[:n])) or 1.0
    return dot / (na * nb)


class VectorStore:
    def __init__(self) -> None:
        self._vectors: list[list[float]] = []
        self._chunks: list[Chunk] = []
        self.embedding_id: str | None = None  # provider:model that produced vectors
        self.dimensions: int | None = None

    def add(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
        embedding_id: str | None = None,
    ) -> None:
        assert len(chunks) == len(vectors), "chunks/vectors length mismatch"
        if vectors:
            dims = {len(v) for v in vectors}
            if len(dims) > 1:
                raise ValueError(f"Inconsistent vector dimensions in batch: {dims}")
            dim = dims.pop()
            # §43: never mix embeddings from different models in one index.
            if self._vectors and (
                dim != self.dimensions or (
                    embedding_id and self.embedding_id and embedding_id != self.embedding_id
                )
            ):
                raise ValueError(
                    f"Embedding mismatch: index has {self.embedding_id} "
                    f"(dim={self.dimensions}), got {embedding_id} (dim={dim}). "
                    "Clear the store before indexing with a different model."
                )
            self.dimensions = dim
            if embedding_id:
                self.embedding_id = embedding_id
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[tuple[Chunk, float]]:
        scored: list[tuple[Chunk, float]] = []
        for chunk, vec in zip(self._chunks, self._vectors):
            if document_id is not None and chunk.document_id != document_id:
                continue  # <-- session isolation: never cross documents
            scored.append((chunk, _cosine(query_vector, vec)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        self._vectors.clear()
        self._chunks.clear()
        self.embedding_id = None
        self.dimensions = None

    def clear_document(self, document_id: str) -> None:
        keep = [(c, v) for c, v in zip(self._chunks, self._vectors)
                if c.document_id != document_id]
        self._chunks = [c for c, _ in keep]
        self._vectors = [v for _, v in keep]
        if not self._chunks:
            self.embedding_id = None
            self.dimensions = None

    def __len__(self) -> int:
        return len(self._chunks)
