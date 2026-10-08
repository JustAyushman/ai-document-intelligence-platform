"""Standalone ingest diagnostic — bypasses Streamlit to surface the REAL error.

Usage:
    python diagnose.py <path-to-your-document.pdf>

Runs the exact same pipeline steps as the app (parse → understand →
preprocess → chunk → embed → store → retrieve) with full tracebacks,
so a Streamlit/session issue can't hide what's happening.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config.settings import settings  # noqa: E402
from document.chunker import create_chunks  # noqa: E402
from document.identifier import identify_document  # noqa: E402
from document.parser import parse_document  # noqa: E402
from document.preprocess import preprocess_document  # noqa: E402
from document.structure import understand_document  # noqa: E402
from llm.client import LLMClient  # noqa: E402
from rag import embeddings  # noqa: E402
from rag.retriever import retrieve  # noqa: E402
from rag.vector_store import VectorStore  # noqa: E402


def step(name):
    print(f"\n=== {name} ===", flush=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python diagnose.py <path-to-document>")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 2

    print(f"key present: {bool(settings.openrouter_api_key)} "
          f"(len={len(settings.openrouter_api_key)})")
    print(f"auto_select: {settings.auto_select_models} | "
          f"emb model: {settings.embedding_model}")

    data = path.read_bytes()
    print(f"file: {path.name} ({len(data)} bytes)")

    try:
        step("1. identify")
        info = identify_document(path.name)
        print("identify:", info)
        if not info["supported"]:
            print("UNSUPPORTED FILE TYPE")
            return 1

        step("2. parse")
        doc = parse_document(path.name, data, info["file_type"])
        print(f"parsed: {doc.page_count} pages, {len(doc.full_text)} chars")

        llm = LLMClient()
        print("llm available:", llm.available)

        step("3. understand (LLM, falls back if offline)")
        structure = understand_document(doc, llm)
        print("doc_type:", structure.get("document_type"),
              "| topics:", structure.get("topics"))

        step("4. preprocess")
        pre = preprocess_document(doc, llm)
        print(f"processed chars: {len(pre['processed_text'])} | notes: {pre['notes']}")

        step("5. chunk")
        chunks = create_chunks(doc, pre["processed_text"], structure)
        print(f"chunks: {len(chunks)}")
        empties = [c.chunk_id for c in chunks if not c.text.strip()]
        print("empty chunks:", empties)
        ctrls = sum(
            sum(1 for ch in c.text if ord(ch) < 32 and ch not in "\n\t")
            for c in chunks
        )
        print("control chars in chunks:", ctrls)

        step("6. embed (REAL API CALL)")
        vectors, choice = embeddings.embed_documents([c.text for c in chunks])
        print(f"vectors: {len(vectors)} | dims: {len(vectors[0])} | used: {choice.model}")

        step("7. store + retrieve")
        store = VectorStore()
        store.add(chunks, vectors, embedding_id=choice.embedding_id)
        print(f"store size: {len(store)} | embedding_id: {store.embedding_id}")
        hits = retrieve("test query about the document", store, doc.document_id, top_k=3)
        print(f"retrieved: {len(hits)} (top score: {hits[0].score:.3f})" if hits
              else "retrieved: NONE")

        print("\nALL STEPS PASSED — indexing works. "
              "If the app still shows 0/N, it is a Streamlit/version issue: "
              "kill ALL streamlit processes and start one fresh 'streamlit run app.py'.")
        return 0
    except Exception:
        print("\n*** FAILED ***")
        traceback.print_exc()
        print("\nPaste the traceback above back for the fix.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
