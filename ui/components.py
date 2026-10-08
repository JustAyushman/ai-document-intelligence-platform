"""Shared UI components: hero, section titles, document card, pipeline viz, reset.

Presentation only — all task/session logic lives in app.py + utils/session.py.
Signatures used by app.py are unchanged.
"""
from __future__ import annotations

import html

from ui.styles import neural_hero_svg
from utils.session import reset_task


def render_hero(st, online: bool) -> None:
    """Brand header + neural visual + system status pill."""
    dot = "ok" if online else "off"
    label = "AI ONLINE" if online else "AI OFFLINE — ADD API KEY"
    st.markdown(
        f"""
<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
  <div>
    <div class="nexus-eyebrow">✦ Nexus AI &nbsp;·&nbsp; Document Intelligence Engine</div>
    <div class="nexus-hero-title">Understand. Retrieve. Generate.</div>
    <div class="nexus-hero-sub">Transform any document into grounded, cited,
    quality-scored AI responses — powered by RAG and automatic model selection.</div>
  </div>
  <div class="nexus-pill"><span class="nexus-dot {dot}"></span>{label}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(neural_hero_svg(), unsafe_allow_html=True)
    st.caption("RAG · GENERATIVE AI · DOCUMENT INTELLIGENCE")


def section_title(st, icon: str, text: str) -> None:
    st.markdown(f'<div class="nexus-section-title">{icon} &nbsp;{html.escape(text)}</div>',
                unsafe_allow_html=True)


def _node(label: str, state: str) -> str:
    mark = {"done": "✓", "active": "◉"}.get(state, "○")
    return f'<span class="nexus-node {state}">{mark} {label}</span>'


def render_pipeline_status(st) -> None:
    """Futuristic pipeline flow: done / active / pending from session state."""
    has_doc = bool(st.session_state.get("document"))
    has_struct = bool(st.session_state.get("doc_structure"))
    has_chunks = bool(st.session_state.get("chunks"))
    from utils.session import VECTOR_STORE_KEY

    store = st.session_state.get(VECTOR_STORE_KEY)
    indexed = len(store) if store is not None else 0
    stages = [
        ("PARSED", "done" if has_doc else "todo"),
        ("UNDERSTOOD", "done" if has_struct else ("active" if has_doc else "todo")),
        ("CHUNKED", "done" if has_chunks else ("active" if has_struct else "todo")),
        ("EMBEDDED", "done" if indexed else ("active" if has_chunks else "todo")),
        ("RAG READY", "done" if indexed else "todo"),
    ]
    flow = '<span class="nexus-link">─</span>'.join(_node(lbl, st8) for lbl, st8 in stages)
    st.markdown(f'<div class="nexus-pipe">{flow}</div>', unsafe_allow_html=True)


def render_document_info(st) -> None:
    meta = st.session_state.get("doc_metadata")
    structure = st.session_state.get("doc_structure")
    chunks = st.session_state.get("chunks") or []
    if not meta:
        return
    from utils.session import VECTOR_STORE_KEY

    indexed = 0
    emb_id = ""
    try:
        store = st.session_state.get(VECTOR_STORE_KEY)
        if store is not None:
            indexed = len(store)
            emb_id = getattr(store, "embedding_id", "") or ""
    except Exception:
        pass
    fname = html.escape(str(meta.get("file_name", "—")))
    ftype = html.escape(str(meta.get("file_type", meta.get("type", "—"))))
    pages = meta.get("page_count", meta.get("pages", "—"))
    topics = []
    if isinstance(structure, dict):
        topics = (structure.get("topics", []) or [])[:6]
    dtype = structure.get("document_type", "—") if isinstance(structure, dict) else "—"
    health = (
        f'<span class="nexus-dot ok"></span> INDEX HEALTHY · {indexed} vectors'
        if indexed >= len(chunks) and chunks
        else f'<span class="nexus-dot warn"></span> INDEX INCOMPLETE · {indexed}/{len(chunks)}'
    )
    topics_html = (
        f"<div class='sub' style='margin-top:8px'>TOPICS · {html.escape(', '.join(topics))}</div>"
        if topics else ""
    )
    st.markdown(
        f"""
<div class="nexus-card glow">
  <div class="nexus-eyebrow">◉ Document Ready</div>
  <div style="font-size:19px;font-weight:800;margin:6px 0 2px 0;">{fname}</div>
  <div class="sub" style="color:#8FA8B8;font-size:12.5px;">
    {ftype.upper()} · {pages} PAGES · {len(chunks)} CHUNKS · {html.escape(str(dtype)).upper()}
  </div>
  <div style="margin-top:10px;font-size:12.5px;">{health}
  <span style="color:#607786;">{(' · ' + html.escape(emb_id)) if emb_id else ''}</span></div>
  {topics_html}
</div>
""",
        unsafe_allow_html=True,
    )
    if indexed < len(chunks):
        st.error(
            f"Index incomplete: {indexed}/{len(chunks)} chunks indexed. "
            "Retrieval will fail — use Re-index below."
        )
    render_pipeline_status(st)
    if isinstance(structure, dict):
        with st.expander("View detected document intelligence"):
            st.json(structure)


def render_empty_state(st) -> None:
    st.markdown(
        """
<div class="nexus-card" style="text-align:center;padding:34px 20px;">
  <div style="font-size:26px;color:#00E5FF;">✦</div>
  <div class="nexus-eyebrow" style="margin-top:8px;">Ready for input</div>
  <div style="color:#8FA8B8;font-size:13.5px;margin:8px 0 0 0;">
  Upload a document and tell the AI what you want to discover.<br>
  It will parse, understand, chunk and index it for grounded RAG answers.</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_reset_button(st, location: str = "main") -> None:
    """First-class 'Start New Task' button with confirmation when data exists."""
    has_data = bool(
        st.session_state.get("document")
        or st.session_state.get("generated_response")
        or st.session_state.get("chunks")
    )
    container = st if location == "main" else st.sidebar
    container.divider()
    container.markdown(
        "<div style='text-align:center;color:#607786;font-size:12px;"
        "letter-spacing:2px;margin-bottom:8px;'>READY FOR ANOTHER DOCUMENT?</div>",
        unsafe_allow_html=True,
    )
    if not st.session_state.get("confirm_reset"):
        if container.button("↻ START NEW TASK", use_container_width=True,
                            help="Clear this task and start fresh."):
            if has_data:
                st.session_state["confirm_reset"] = True
                st.rerun()
            else:
                reset_task(st)
                st.rerun()
    else:
        container.warning(
            "Start a new task? This clears the document, context, results, and RAG data."
        )
        col1, col2 = container.columns(2)
        if col1.button("Cancel", use_container_width=True):
            st.session_state["confirm_reset"] = False
            st.rerun()
        if col2.button("Start New Task", type="primary", use_container_width=True):
            reset_task(st)
            st.success("Everything is cleared — ready for a new task.")
            st.rerun()
