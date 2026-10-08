"""Upload step: styled neural upload card + file uploader (behavior unchanged)."""
from __future__ import annotations

from config.settings import settings


def render_upload(st) -> tuple | None:
    st.markdown(
        f"""
<div class="nexus-card glow" style="text-align:center;padding:28px 20px;margin-bottom:4px;">
  <div style="font-size:24px;color:#00E5FF;">◉</div>
  <div class="nexus-eyebrow" style="margin-top:6px;">Drop your document here</div>
  <div style="color:#8FA8B8;font-size:12.5px;letter-spacing:2px;margin-top:6px;">
  PDF · DOCX · TXT &nbsp;(max ~{settings.max_upload_mb} MB)</div>
  <div style="color:#607786;font-size:12px;margin-top:8px;">
  AI will understand the structure, create semantic chunks and index it for RAG.</div>
</div>
""",
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Browse files",
        type=["pdf", "docx", "doc", "txt", "md"],
        help=f"Max ~{settings.max_upload_mb} MB. Text is extracted locally; only prompts go to OpenRouter.",
        label_visibility="collapsed",
    )
    if uploaded is None:
        return None
    size_mb = len(uploaded.getvalue()) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        st.error(f"File is {size_mb:.1f} MB — limit is {settings.max_upload_mb} MB.")
        return None
    st.caption(f"◉ {uploaded.name} — {size_mb:.2f} MB")
    return uploaded
