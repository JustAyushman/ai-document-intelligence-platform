"""Multi-chat workspace manager (pure functions, no Streamlit dependency).

One document + one shared RAG index, many independent chats.
Creating/switching/deleting chats never touches document data —
only Start New Task clears document + RAG + all chats.
"""
from __future__ import annotations

import re
import time
import uuid

# Words skipped when deriving a short title from the first question.
_TITLE_STOPWORDS = {
    "what", "is", "are", "was", "were", "explain", "give", "me", "my",
    "the", "a", "an", "of", "about", "to", "for", "and", "how", "why",
    "when", "where", "which", "who", "do", "does", "did", "can", "could",
    "please", "tell", "show", "list", "find", "get", "all", "give",
}

# How many recent exchanges are folded into a follow-up (token control).
MAX_HISTORY_TURNS = 3


def new_chat_id() -> str:
    return f"chat_{uuid.uuid4().hex[:8]}"


def get_chats(session_state: dict) -> dict:
    return session_state.get("chats") or {}


def create_chat(session_state: dict, document_id: str) -> dict:
    """Create an empty chat on the CURRENT document. No reprocessing."""
    chats = get_chats(session_state)
    chat = {
        "chat_id": new_chat_id(),
        "document_id": document_id,
        "title": "New Chat",
        "messages": [],
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    chats[chat["chat_id"]] = chat
    session_state["chats"] = chats
    session_state["active_chat_id"] = chat["chat_id"]
    return chat


def ensure_chat(session_state: dict, document_id: str) -> dict:
    """Return the active chat for this document, creating one if needed."""
    chats = get_chats(session_state)
    active_id = session_state.get("active_chat_id")
    chat = chats.get(active_id) if active_id else None
    if chat is not None and chat.get("document_id") == document_id:
        return chat
    # Prefer the most recent chat of this document, else create one.
    for c in reversed(list(chats.values())):
        if c.get("document_id") == document_id:
            session_state["active_chat_id"] = c["chat_id"]
            return c
    return create_chat(session_state, document_id)


def delete_chat(session_state: dict, chat_id: str) -> None:
    """Delete ONE chat's history only. Document, RAG and other chats stay."""
    chats = get_chats(session_state)
    chats.pop(chat_id, None)
    session_state["chats"] = chats
    if session_state.get("active_chat_id") == chat_id:
        session_state["active_chat_id"] = None


def derive_title(first_question: str) -> str:
    """Short deterministic title from the first message (no LLM call)."""
    words = re.findall(r"[A-Za-z0-9']+", first_question or "")
    meaningful = [w for w in words if w.lower() not in _TITLE_STOPWORDS]
    picked = (meaningful or words)[:4]
    title = " ".join(picked).title()
    return (title[:36] + "…") if len(title) > 36 else (title or "New Chat")


def retitle_from_first_message(chat: dict) -> None:
    for m in chat.get("messages", []):
        if m.get("role") == "user" and m.get("content", "").strip():
            chat["title"] = derive_title(m["content"])
            return


def build_contextual_query(messages: list, new_question: str) -> str:
    """Fold recent turns of THIS chat into the query (conversational RAG).

    Factual grounding still comes from the document's RAG index; history
    only resolves references like 'it' / 'this' / 'that section'.
    """
    prior = [m for m in messages if m.get("role") in ("user", "assistant")]
    prior = prior[-(MAX_HISTORY_TURNS * 2):]
    if not prior:
        return new_question
    lines = []
    for m in prior:
        who = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{who}: {m.get('content', '')[:600]}")
    return (
        "Conversation so far in this chat:\n" + "\n".join(lines)
        + "\n\nFollow-up question (resolve pronouns like 'it'/'this' "
        + "using the conversation above): " + new_question
    )
