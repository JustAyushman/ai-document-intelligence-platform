"""RAG pipeline: the readable end-to-end flow.

    ingest(document) -> chunks stored with embeddings
    answer(query)    -> retrieve -> generate -> validate -> evaluate

Model selection is automatic (§33): the pipeline asks the selectors
for the right LLM and embedding model — the workflow itself never changes
regardless of which models are picked (§49).
"""
from __future__ import annotations

from config.settings import settings
from document.chunker import create_chunks
from document.preprocess import preprocess_document
from document.structure import understand_document
from llm.evaluation import evaluate_quality
from llm.generation import generate_response
from llm.model_selector import TaskContext, select_llm
from llm.requirement_understanding import understand_requirement
from models.schemas import ParsedDocument
from rag import embeddings
from rag.retriever import retrieve
from rag.vector_store import VectorStore


class RAGPipeline:
    def __init__(self, llm_client, store: VectorStore | None = None) -> None:
        self.llm = llm_client
        # NOTE: must be `is not None`, NEVER `store or VectorStore()`.
        # VectorStore defines __len__, so an EMPTY store is falsy — `or`
        # would silently swap in a throwaway store and every ingest would
        # index into the void while the session's store stayed empty.
        self.store = store if store is not None else VectorStore()
        self.model_config: dict = {}  # task-level config (§44), surfaced in UI

    # --- ingest side ---
    def ingest(self, doc: ParsedDocument) -> dict:
        """Parse -> understand -> preprocess -> chunk -> embed -> store.

        Order matters: embeddings are generated BEFORE the old index is
        cleared, so a failed ingest never wipes a working index (which
        used to surface later as the confusing 'No relevant chunks found').
        """
        structure = understand_document(doc, self.llm)
        pre = preprocess_document(doc, self.llm)
        chunks = create_chunks(doc, pre["processed_text"], structure)
        if not chunks:
            raise ValueError("Chunking produced no chunks — the document may be empty.")
        # Embed first (may raise with a specific provider error)...
        vectors, emb_choice = embeddings.embed_documents([c.text for c in chunks])
        if not vectors:
            raise RuntimeError("Embedding service returned no vectors.")
        # ...only then replace the index (atomic swap, never a half-empty store).
        self.store.clear()
        self.store.add(chunks, vectors, embedding_id=emb_choice.embedding_id)
        self.model_config = {
            "task_id": "",
            "document_id": doc.document_id,
            "selected_llm": "",  # chosen at answer time (depends on the task)
            "llm_reason": "",
            "embedding_provider": emb_choice.provider,
            "embedding_model": emb_choice.model,
            "embedding_dimensions": emb_choice.dimensions,
            "embedding_reason": emb_choice.reason,
        }
        knowledge = {
            "document_id": doc.document_id,
            "file_name": doc.file_name,
            "structure": structure,
            "chunk_count": len(chunks),
            "preprocess_notes": pre["notes"],
        }
        return {"chunks": chunks, "preprocessed": pre,
                "structure": structure, "knowledge": knowledge,
                "model_config": dict(self.model_config)}

    # --- query side ---
    def answer(
        self,
        user_text: str,
        document_id: str,
        task_hint: str = "custom",
        top_k: int | None = None,
        metadata_filter: dict | None = None,
        doc_chars: int = 0,
    ) -> dict:
        spec = understand_requirement(user_text, task_hint, self.llm)
        if len(self.store) == 0:
            return {
                "spec": spec, "context": [], "response": "",
                "prompt": "", "validation": {"is_valid": False, "issues": ["Document index is empty."]},
                "quality": None,
                "error": (
                    "The document index is empty — indexing did not complete. "
                    "Please re-upload the document (any processing error is shown "
                    "during the upload step)."
                ),
                "model_config": dict(self.model_config),
            }
        # Automatic LLM selection for THIS task (§34–§36).
        llm_choice = select_llm(TaskContext(
            intent=spec.intent or task_hint,
            doc_chars=doc_chars,
            chunk_count=len(self.store),
            needs_reasoning=(spec.intent in ("generate", "custom")),
        ))
        self.model_config.update({
            "selected_llm": llm_choice.model,
            "llm_reason": llm_choice.reason,
        })
        context = retrieve(spec, self.store, document_id,
                           top_k=top_k or settings.top_k,
                           metadata_filter=metadata_filter)
        if not context:
            return {
                "spec": spec, "context": [], "response": "",
                "prompt": "", "validation": {"is_valid": False, "issues": ["No relevant content retrieved."]},
                "quality": None, "error": "No relevant chunks found. Try rephrasing.",
                "model_config": dict(self.model_config),
            }
        response, prompt, validation = generate_response(
            context, spec, self.llm, model=llm_choice.model
        )
        quality = evaluate_quality(response, spec, context, self.llm)
        return {
            "spec": spec, "context": context, "response": response,
            "prompt": prompt, "validation": validation,
            "quality": quality.as_dict(), "error": None,
            "model_config": dict(self.model_config),
        }
