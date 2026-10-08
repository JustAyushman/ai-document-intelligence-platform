"""AI Document Intelligence Platform — Streamlit entry point.

Readable orchestration (the whole pipeline in one glance):

    document = parse_document(file)
    chunks   = create_chunks(document)   [via RAGPipeline.ingest]
    query    = understand_requirement(user_input)
    context  = retrieve(query)
    response = generate_response(context, query)
    validated = validate(response)  (+ repair loop inside generation)
    quality  = evaluate(response)
"""
from __future__ import annotations

import traceback

import streamlit as st

from config.settings import settings
from document.identifier import identify_document
from document.parser import parse_document
from llm.client import client as llm_client
from rag.pipeline import RAGPipeline
from rag.vector_store import VectorStore
from ui.components import (
    render_document_info,
    render_empty_state,
    render_hero,
    render_reset_button,
    section_title,
)
from chat import manager as chats
from ui.chat import render_message
from ui.sidebar import render_sidebar
from ui.styles import inject_styles
from ui.upload import render_upload
from utils.logging import get_logger, persist_error, persist_info
from utils.session import VECTOR_STORE_KEY, init_task_state

log = get_logger(__name__)

st.set_page_config(page_title="AI Document Intelligence Platform", layout="wide")

TASK_OPTIONS = [
    ("summarize", "SUMMARY"),
    ("extract", "EXTRACT"),
    ("classify", "CLASSIFY"),
    ("retrieve", "RETRIEVE"),
    ("generate", "GENERATE"),
    ("custom", "CUSTOM"),
]


def get_pipeline() -> RAGPipeline:
    if VECTOR_STORE_KEY not in st.session_state:
        st.session_state[VECTOR_STORE_KEY] = VectorStore()
    return RAGPipeline(llm_client, st.session_state[VECTOR_STORE_KEY])


def process_upload(file_name: str, data: bytes) -> tuple:
    """Identify → parse → ingest. Raises with a specific message on failure.

    Bytes are kept in session state so a failed/lost index can be rebuilt
    with one click (Re-index) instead of forcing another upload.
    """
    info = identify_document(file_name)
    if not info["supported"]:
        raise ValueError(f"Unsupported file: {file_name}. Use PDF, DOCX, or TXT.")
    doc = parse_document(file_name, data, info["file_type"])
    out = get_pipeline().ingest(doc)
    st.session_state["upload_bytes"] = data
    st.session_state["document"] = {
        "document_id": doc.document_id,
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "full_text": doc.full_text,
    }
    st.session_state["doc_metadata"] = {
        "file_name": doc.file_name, "file_type": doc.file_type,
        "page_count": doc.page_count, **doc.metadata,
    }
    st.session_state["doc_structure"] = out["structure"]
    st.session_state["preprocessed"] = out["preprocessed"]
    st.session_state["chunks"] = out["chunks"]
    st.session_state["model_config"] = out.get("model_config")
    st.session_state["stage"] = "ready"
    mc = out.get("model_config") or {}
    persist_info(
        "ingest-ok",
        f"{file_name}: {len(out['chunks'])} chunks, "
        f"{mc.get('embedding_model')} ({mc.get('embedding_dimensions')}d)",
    )
    return doc, out


def friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "API key" in msg or "401" in msg:
        return "LLM authentication failed. Check OPENROUTER_API_KEY in your .env."
    if "rate limit" in msg or "429" in msg:
        return "The LLM service is rate-limited. Wait a moment and retry."
    if "Embedding" in msg or "embedding" in msg:
        return f"Embedding service issue: {msg}"
    if "request failed" in msg or "timeout" in msg.lower():
        return "Could not reach the LLM service. Check your connection and retry."
    return msg


def main() -> None:
    init_task_state(st)
    inject_styles(st)
    render_hero(st, online=llm_client.available)

    cfg = render_sidebar(st)

    # ---------- 1. Upload + identify + parse + ingest ----------
    section_title(st, "↑", "01 · Document Intake")
    uploaded = render_upload(st)
    if uploaded is None and not st.session_state.get("document"):
        render_empty_state(st)
    if uploaded is not None:
        already = st.session_state.get("document")
        if already is None or already.get("file_name") != uploaded.name:
            with st.spinner("Processing document: parse → understand → chunk → embed…"):
                try:
                    doc, out = process_upload(uploaded.name, uploaded.getvalue())
                    st.session_state["error"] = None
                    # Verify (don't assume): report the ACTUAL live index size.
                    live_index = len(get_pipeline().store)
                    st.success(
                        f"Document ready: {doc.page_count} page(s), "
                        f"{len(out['chunks'])} chunks, "
                        f"{live_index} vectors in index."
                    )
                except Exception as exc:
                    log.error("Document processing failed: %s\n%s", exc, traceback.format_exc())
                    persist_error(f"upload {uploaded.name}", exc)
                    st.session_state["error"] = friendly_error(exc)
                    st.error(f"Could not process document: {st.session_state['error']}")

    render_document_info(st)

    # ---------- 1b. Index health check + one-click recovery ----------
    if st.session_state.get("chunks") and len(get_pipeline().store) == 0:
        st.warning(
            "⚠️ The document index is empty (indexing did not complete), "
            "so retrieval cannot work yet."
        )
        if st.session_state.get("error"):
            st.error(f"Last processing error: {st.session_state['error']}")
        if st.session_state.get("upload_bytes") and st.button(
            "🔄 Re-index document", use_container_width=True
        ):
            with st.spinner("Re-indexing document…"):
                try:
                    doc, out = process_upload(
                        st.session_state["document"]["file_name"],
                        st.session_state["upload_bytes"],
                    )
                    st.session_state["error"] = None
                    st.success(f"Re-indexed: {len(out['chunks'])} chunks.")
                    st.rerun()
                except Exception as exc:
                    log.error("Re-index failed: %s\n%s", exc, traceback.format_exc())
                    persist_error("re-index", exc)
                    st.session_state["error"] = friendly_error(exc)
                    st.error(f"Re-index failed: {st.session_state['error']}")

    # ---------- 2. Multi-chat conversational workspace ----------
    # One shared document + RAG index; each chat keeps its own history.
    if st.session_state.get("chunks"):
        doc_state = st.session_state["document"]
        chat = chats.ensure_chat(st.session_state, doc_state["document_id"])
        section_title(st, "✦", f"02 · Conversation — {chat.get('title', 'New Chat')}")
        for msg in chat.get("messages", []):
            render_message(st, msg)

        cols = st.columns(len(TASK_OPTIONS))
        for i, (key, label) in enumerate(TASK_OPTIONS):
            if cols[i].button(label, use_container_width=True,
                              type="primary" if st.session_state.get("task_hint") == key else "secondary"):
                st.session_state["task_hint"] = key
        task_hint = st.session_state.get("task_hint") or "custom"

        user_text = st.text_area(
            "Ask a follow-up about this document:",
            value=st.session_state.get("user_requirement") or "",
            placeholder="e.g. What is aperture? / Summarize the lighting section… (follow-ups understand 'it', 'this', …)",
            height=110,
        )
        send_cols = st.columns([5, 1])
        run = send_cols[1].button("SEND →", type="primary", use_container_width=True)
        if run:
            if not user_text.strip():
                st.warning("Please describe what you want first.")
            elif not llm_client.available:
                st.error("OPENROUTER_API_KEY is not set. Add it to .env to enable generation.")
            else:
                question = user_text.strip()
                user_msg = {"role": "user", "content": question, "task": task_hint}
                # Self-heal: if the index was lost but we kept the file bytes,
                # rebuild it automatically instead of failing retrieval.
                healed = True
                if len(get_pipeline().store) == 0 and st.session_state.get("upload_bytes"):
                    with st.spinner("Index empty — rebuilding automatically…"):
                        try:
                            process_upload(
                                st.session_state["document"]["file_name"],
                                st.session_state["upload_bytes"],
                            )
                            st.session_state["error"] = None
                        except Exception as exc:
                            log.error("Auto re-index failed: %s\n%s", exc, traceback.format_exc())
                            persist_error("auto-reindex", exc)
                            st.session_state["error"] = friendly_error(exc)
                            st.error(
                                "Could not rebuild the index: "
                                f"{st.session_state['error']}"
                            )
                            healed = False
                if healed:
                    with st.spinner("Understanding → retrieving → generating → validating…"):
                        try:
                            pipeline = get_pipeline()
                            augmented = chats.build_contextual_query(
                                chat["messages"], question
                            )
                            result = pipeline.answer(
                                augmented, doc_state["document_id"],
                                task_hint=task_hint,
                                top_k=cfg["top_k"],
                                doc_chars=len(doc_state.get("full_text", "")),
                            )
                            chat["messages"].append(user_msg)
                            if result.get("response"):
                                spec = result["spec"]
                                spec_d = spec if isinstance(spec, dict) else spec.__dict__
                                sources = []
                                for rc in result.get("context") or []:
                                    c = rc.chunk if hasattr(rc, "chunk") else rc.get("chunk")
                                    s = rc.score if hasattr(rc, "score") else rc.get("score", 0)
                                    sources.append({
                                        "chunk_id": getattr(c, "chunk_id", ""),
                                        "page_number": getattr(c, "page_number", 0),
                                        "section": getattr(c, "section", ""),
                                        "heading": getattr(c, "heading", ""),
                                        "score": round(float(s), 3),
                                        "text": getattr(c, "text", "")[:1500],
                                    })
                                mc = result.get("model_config") or {}
                                chat["messages"].append({
                                    "role": "assistant",
                                    "content": result["response"],
                                    "task": task_hint,
                                    "spec": spec_d,
                                    "sources": sources,
                                    "quality": result.get("quality") or {},
                                    "validation": result.get("validation") or {},
                                    "model": mc.get("selected_llm", ""),
                                })
                            chats.retitle_from_first_message(chat)
                            st.session_state["user_requirement"] = ""
                            st.session_state["error"] = None
                            if result.get("error"):
                                st.warning(result["error"])
                            st.rerun()
                        except Exception as exc:
                            log.error("Generation failed: %s\n%s", exc, traceback.format_exc())
                            persist_error("generate", exc)
                            st.error(f"Generation failed: {friendly_error(exc)}")

        # Regenerate the last answer (same question, fresh LLM call).
        msgs = chat.get("messages", [])
        if len(msgs) >= 2 and msgs[-1].get("role") == "assistant" \
                and msgs[-2].get("role") == "user":
            if st.button("↻ Regenerate last answer", use_container_width=False):
                with st.spinner("Regenerating…"):
                    try:
                        last_q = msgs[-2]
                        chat["messages"] = msgs[:-1]
                        augmented = chats.build_contextual_query(
                            chat["messages"][:-1], last_q["content"]
                        )
                        result = get_pipeline().answer(
                            augmented, doc_state["document_id"],
                            task_hint=last_q.get("task", "custom"),
                            top_k=cfg["top_k"],
                            doc_chars=len(doc_state.get("full_text", "")),
                        )
                        if result.get("response"):
                            mc = result.get("model_config") or {}
                            spec = result["spec"]
                            chat["messages"].append({
                                "role": "assistant",
                                "content": result["response"],
                                "task": last_q.get("task", "custom"),
                                "spec": spec if isinstance(spec, dict) else spec.__dict__,
                                "sources": [{
                                    "chunk_id": getattr(
                                        rc.chunk if hasattr(rc, "chunk") else rc.get("chunk"),
                                        "chunk_id", ""),
                                    "page_number": getattr(
                                        rc.chunk if hasattr(rc, "chunk") else rc.get("chunk"),
                                        "page_number", 0),
                                    "section": getattr(
                                        rc.chunk if hasattr(rc, "chunk") else rc.get("chunk"),
                                        "section", ""),
                                    "heading": getattr(
                                        rc.chunk if hasattr(rc, "chunk") else rc.get("chunk"),
                                        "heading", ""),
                                    "score": round(float(
                                        rc.score if hasattr(rc, "score") else rc.get("score", 0)), 3),
                                    "text": getattr(
                                        rc.chunk if hasattr(rc, "chunk") else rc.get("chunk"),
                                        "text", "")[:1500],
                                } for rc in result.get("context") or []],
                                "quality": result.get("quality") or {},
                                "validation": result.get("validation") or {},
                                "model": mc.get("selected_llm", ""),
                            })
                        if result.get("error"):
                            st.warning(result["error"])
                        st.rerun()
                    except Exception as exc:
                        log.error("Regenerate failed: %s\n%s", exc, traceback.format_exc())
                        persist_error("regenerate", exc)
                        st.error(f"Regenerate failed: {friendly_error(exc)}")

    # ---------- 3. First-class reset ----------
    render_reset_button(st, location="main")


if __name__ == "__main__":
    main()
