"""Sidebar: brand, conversations, workspace status, system status, tuning."""
from __future__ import annotations

from config.settings import settings
from ui.chat import render_conversations
from utils.session import VECTOR_STORE_KEY


def _dot(ok: bool | None) -> str:
    cls = "ok" if ok else ("warn" if ok is None else "off")
    return f'<span class="nexus-dot {cls}"></span>'


def render_sidebar(st) -> dict:
    st.sidebar.markdown(
        """
<div style="margin:6px 0 2px 0;">
  <div style="font-size:15px;font-weight:800;letter-spacing:2px;">
  <span style="color:#00E5FF;">✦</span> NEXUS AI</div>
  <div style="font-size:10px;letter-spacing:3px;color:#607786;">DOCUMENT INTELLIGENCE</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    # --- workspace / pipeline status (visual, derived from session) ---
    has_doc = bool(st.session_state.get("document"))
    has_chunks = bool(st.session_state.get("chunks"))
    has_answer = bool(st.session_state.get("generated_response"))
    store = st.session_state.get(VECTOR_STORE_KEY)
    indexed = len(store) if store is not None else 0
    st.sidebar.markdown(
        f"""
<div class="nexus-eyebrow" style="margin-bottom:8px;">Workspace</div>
<div style="font-size:12.5px;color:#8FA8B8;line-height:2;">
{_dot(has_doc)} Document<br>
{_dot(bool(st.session_state.get("doc_structure")))} Understanding<br>
{_dot(indexed > 0)} Retrieval <span style="color:#607786;">({indexed} vectors)</span><br>
{_dot(has_answer)} Generation<br>
{_dot(bool(st.session_state.get("validation_result")))} Validation<br>
{_dot(bool(st.session_state.get("quality_result")))} Evaluation
</div>
""",
        unsafe_allow_html=True,
    )
    st.sidebar.divider()
    render_conversations(st)
    if st.session_state.get("document"):
        st.sidebar.divider()

    # --- system status ---
    llm_ok = settings.llm_configured
    st.sidebar.markdown(
        f"""
<div class="nexus-eyebrow" style="margin-bottom:8px;">System</div>
<div style="font-size:12.5px;color:#8FA8B8;line-height:2;">
{_dot(llm_ok)} LLM {'Ready' if llm_ok else 'No API key'}<br>
{_dot(True)} RAG Engine<br>
{_dot(True)} Embeddings API
</div>
""",
        unsafe_allow_html=True,
    )
    if not llm_ok:
        st.sidebar.warning("OPENROUTER_API_KEY not set — add it to .env.")
    if settings.auto_select_models:
        st.sidebar.caption("Models: automatic (per-task selection)")
    else:
        st.sidebar.caption("Models: manual override")

    st.sidebar.divider()
    st.sidebar.markdown('<div class="nexus-eyebrow">Retrieval Tuning</div>',
                        unsafe_allow_html=True)
    top_k = st.sidebar.slider("Top-K sources", 1, 10, settings.top_k)
    temperature = st.sidebar.slider("Creativity", 0.0, 1.0, 0.3, 0.05)

    with st.sidebar.expander("About NEXUS AI"):
        st.markdown(
            "Document-type independent RAG platform. Python orchestrates; "
            "the LLM understands, retrieves context, and generates. "
            "Models are selected automatically per task."
        )
    return {"top_k": top_k, "temperature": temperature}
