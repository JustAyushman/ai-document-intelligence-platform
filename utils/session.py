"""Streamlit task-state management.

Separates APPLICATION state (config, never cleared) from TASK state
(document, RAG data, results — cleared on 'Start New Task').
"""
from __future__ import annotations

TASK_KEYS = [
    "task_id",
    "task_hint",
    "upload_bytes",
    "document",
    "doc_metadata",
    "doc_structure",
    "preprocessed",
    "chunks",
    "model_config",
    "user_requirement",
    "requirement_spec",
    "retrieved_context",
    "prompt_text",
    "generated_response",
    "validation_result",
    "quality_result",
    "error",
    "stage",
    "confirm_reset",
    "chats",
    "active_chat_id",
]

VECTOR_STORE_KEY = "_vector_store"


def init_task_state(st) -> None:
    """Ensure every task key exists in session_state."""
    import uuid

    for key in TASK_KEYS:
        if key not in st.session_state:
            st.session_state[key] = None
    if not st.session_state.get("task_id"):
        st.session_state["task_id"] = f"task_{uuid.uuid4().hex[:8]}"
    if "confirm_reset" not in st.session_state or st.session_state["confirm_reset"] is None:
        st.session_state["confirm_reset"] = False
    if not st.session_state.get("stage"):
        st.session_state["stage"] = "upload"


def reset_task(st) -> None:
    """Clear ALL current task/session data and start a fresh task.

    Does NOT touch API keys, settings, or code — only task-level data.
    Also clears the in-memory RAG store so Document A can never leak
    into Document B's retrieval.
    """
    import uuid

    # Clear the RAG vector store (session isolation).
    if VECTOR_STORE_KEY in st.session_state:
        try:
            store = st.session_state[VECTOR_STORE_KEY]
            if hasattr(store, "clear"):
                store.clear()
        except Exception:
            pass
        del st.session_state[VECTOR_STORE_KEY]

    for key in TASK_KEYS:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["task_id"] = f"task_{uuid.uuid4().hex[:8]}"
    st.session_state["stage"] = "upload"
    st.session_state["confirm_reset"] = False
    for key in TASK_KEYS:
        if key not in st.session_state:
            st.session_state[key] = None
    st.session_state["task_id"] = st.session_state["task_id"]
