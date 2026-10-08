"""Document parsing: bytes -> ParsedDocument (pages + metadata).

Each parser preserves page numbers and best-effort headings/sections.
Failures raise a friendly ValueError (UI catches and shows cleanly).
"""
from __future__ import annotations

import io
import re

from models.schemas import PageContent, ParsedDocument
from utils.helpers import clean_whitespace, new_id
from utils.logging import get_logger

log = get_logger(__name__)


def parse_document(file_name: str, file_bytes: bytes, file_type: str) -> ParsedDocument:
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")
    if file_type == "pdf":
        return _parse_pdf(file_name, file_bytes)
    if file_type == "docx":
        return _parse_docx(file_name, file_bytes)
    if file_type == "txt":
        return _parse_txt(file_name, file_bytes)
    raise ValueError(f"Unsupported file type: {file_type!r}. Use PDF, DOCX, or TXT.")


def _parse_pdf(file_name: str, file_bytes: bytes) -> ParsedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF support needs 'pypdf'. Run: pip install -r requirements.txt") from exc
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc
    pages: list[PageContent] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = clean_whitespace(text)
        heading, section = _guess_heading_section(text)
        pages.append(PageContent(page_number=i, text=text, heading=heading, section=section))
    meta = {}
    try:
        info = reader.metadata or {}
        meta = {str(k).strip("/"): str(v) for k, v in dict(info).items()}
    except Exception:
        pass
    meta.update({"page_count": len(pages), "source": file_name})
    doc = ParsedDocument(
        document_id=new_id("doc"), file_name=file_name,
        file_type="pdf", pages=pages, metadata=meta,
    )
    if not doc.full_text.strip():
        raise ValueError("No extractable text found in this PDF (it may be scanned images).")
    return doc


def _parse_docx(file_name: str, file_bytes: bytes) -> ParsedDocument:
    try:
        import docx
    except ImportError as exc:
        raise ValueError("DOCX support needs 'python-docx'. Run: pip install -r requirements.txt") from exc
    try:
        d = docx.Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Could not read DOCX: {exc}") from exc
    # Group paragraphs into pseudo-pages (~600 words each) since DOCX has no pages.
    paras = [clean_whitespace(p.text) for p in d.paragraphs if p.text and p.text.strip()]
    # Attach heading styles where available.
    headings: list[str] = []
    try:
        for p in d.paragraphs:
            if p.text and p.text.strip() and p.style and p.style.name.startswith("Heading"):
                headings.append(clean_whitespace(p.text))
    except Exception:
        pass
    pages: list[PageContent] = []
    buf: list[str] = []
    words = 0
    page_no = 1
    for para in paras:
        buf.append(para)
        words += len(para.split())
        if words >= 600:
            text = clean_whitespace("\n".join(buf))
            h, s = _guess_heading_section(text)
            pages.append(PageContent(page_number=page_no, text=text, heading=h, section=s))
            buf, words, page_no = [], 0, page_no + 1
    if buf:
        text = clean_whitespace("\n".join(buf))
        h, s = _guess_heading_section(text)
        pages.append(PageContent(page_number=page_no, text=text, heading=h, section=s))
    if not pages:
        raise ValueError("No extractable text found in this document.")
    core = {}
    try:
        cp = d.core_properties
        core = {
            "title": cp.title or "", "author": cp.author or "",
            "subject": cp.subject or "", "created": str(cp.created or ""),
        }
    except Exception:
        pass
    core.update({"page_count": len(pages), "source": file_name})
    return ParsedDocument(
        document_id=new_id("doc"), file_name=file_name,
        file_type="docx", pages=pages, metadata=core,
    )


def _parse_txt(file_name: str, file_bytes: bytes) -> ParsedDocument:
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8", errors="replace")
    text = clean_whitespace(text)
    if not text:
        raise ValueError("Text file is empty.")
    # Pseudo-pages of ~600 words for uniform downstream handling.
    words = text.split()
    pages: list[PageContent] = []
    size = 600
    for i in range(0, len(words), size):
        chunk = " ".join(words[i:i + size])
        h, s = _guess_heading_section(chunk)
        pages.append(PageContent(page_number=len(pages) + 1, text=chunk, heading=h, section=s))
    return ParsedDocument(
        document_id=new_id("doc"), file_name=file_name, file_type="txt",
        pages=pages, metadata={"page_count": len(pages), "source": file_name},
    )


def _guess_heading_section(text: str) -> tuple[str, str]:
    """Best-effort structural hint only — the LLM does real understanding later."""
    if not text:
        return "", ""
    first_lines = [ln.strip() for ln in text.split("\n") if ln.strip()][:5]
    heading = ""
    for ln in first_lines:
        if len(ln) < 120 and (ln.isupper() or re.match(r"^(chapter|section|part)\b", ln, re.I)):
            heading = ln
            break
    if not heading and first_lines:
        heading = first_lines[0][:100]
    section = ""
    m = re.search(r"(section\s+[A-Z0-9.\-]+)", text, re.I)
    if m:
        section = m.group(1).strip()
    return heading, section
