"""Chat workspace presentation: conversation list, message cards, quality bars.

Stateless rendering over st.session_state['chats']; all mutations go
through chat.manager (pure functions). Square technical aesthetic.
"""
from __future__ import annotations

import html

from chat import manager as chats


def quality_bars_html(quality: dict) -> str:
    rows = [
        ("RELEVANCE", quality.get("relevance", 0)),
        ("FACTUALITY", quality.get("factuality", 0)),
        ("CONSISTENCY", quality.get("consistency", 0)),
        ("COMPLETENESS", quality.get("completeness", 0)),
        ("FORMAT", quality.get("format_compliance", quality.get("format", 0))),
    ]
    parts = []
    for name, score in rows:
        score = max(0, min(100, int(score or 0)))
        parts.append(
            f'<div class="nexus-qbar"><div class="lbl">{name}</div>'
            f'<div class="track"><div class="fill" style="width:{score}%"></div></div>'
            f'<div class="val">{score}%</div></div>'
        )
    return "".join(parts)


def render_conversations(st) -> None:
    """Sidebar panel: + NEW CHAT, selectable chats, per-chat delete."""
    doc = st.session_state.get("document")
    if not doc:
        return
    st.sidebar.markdown('<div class="nexus-eyebrow" style="margin-bottom:8px;">Conversations</div>',
                        unsafe_allow_html=True)
    if st.sidebar.button("+ NEW CHAT", use_container_width=True,
                         help="New conversation on the same document (no reprocessing)."):
        chats.create_chat(st.session_state, doc["document_id"])
        st.toast("New chat started — same document, fresh history.")
        st.rerun()
    all_chats = chats.get_chats(st.session_state)
    mine = [c for c in all_chats.values() if c.get("document_id") == doc["document_id"]]
    active_id = st.session_state.get("active_chat_id")
    for c in reversed(mine):  # newest first
        title = (c.get("title") or "New Chat")[:28]
        row = st.sidebar.columns([5, 1])
        is_active = c["chat_id"] == active_id
        if row[0].button(
            (("▸ " if is_active else "· ") + title),
            key=f"chat_{c['chat_id']}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state["active_chat_id"] = c["chat_id"]
            st.rerun()
        if row[1].button("×", key=f"del_{c['chat_id']}",
                         help="Delete this chat only (document + RAG stay)."):
            chats.delete_chat(st.session_state, c["chat_id"])
            st.toast("Chat deleted — document and other chats kept.")
            st.rerun()


def render_message(st, msg: dict) -> None:
    """One square YOU / AI panel. AI panels carry sources + quality."""
    role = msg.get("role", "user")
    content = msg.get("content", "")
    if role == "user":
        st.markdown(
            f'<div class="nexus-msg user"><div class="who">YOU</div>'
            f'<div>{html.escape(content)}</div></div>',
            unsafe_allow_html=True,
        )
        return
    task = html.escape(str(msg.get("task", "custom")).upper())
    quality = msg.get("quality") or {}
    overall = quality.get("overall", "")
    model = msg.get("model", "")
    meta_bits = [f"✦ AI · {task}"]
    if model:
        meta_bits.append(html.escape(str(model).split("/")[-1]))
    if overall != "":
        meta_bits.append(f"◎ {overall}%")
    st.markdown(
        f'<div class="nexus-msg ai"><div class="who">{" · ".join(meta_bits)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(content)
    val = msg.get("validation") or {}
    if val and not val.get("is_valid", True):
        st.warning("Validation flagged: " + "; ".join(val.get("issues", [])))
    sources = msg.get("sources") or []
    if sources:
        with st.expander(f"⌁ Sources ({len(sources)})"):
            for i, s in enumerate(sources, start=1):
                sub = f"Page {s.get('page_number', '?')}"
                if s.get("section"):
                    sub += f" · {html.escape(str(s['section']))}"
                if s.get("heading"):
                    sub += f" · {html.escape(str(s['heading'])[:60])}"
                st.markdown(
                    f'<div class="nexus-src"><div class="num">{i:02d}</div>'
                    f'<div><div class="meta">{html.escape(str(s.get("chunk_id", "")))}</div>'
                    f'<div class="sub">{sub}</div></div></div>',
                    unsafe_allow_html=True,
                )
                text = s.get("text", "")
                st.caption((text[:400] + "…") if len(text) > 400 else text)
    if quality:
        with st.expander(f"◎ Quality ({overall}%)" if overall != "" else "◎ Quality"):
            st.markdown(quality_bars_html(quality), unsafe_allow_html=True)
            if quality.get("notes"):
                st.caption(quality["notes"])
    st.markdown("</div>", unsafe_allow_html=True)
