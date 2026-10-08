"""Intelligent / semantic chunking.

Strategy (RAG-friendly, easy to follow):
  1. Split processed text on semantic boundaries (headings, blank lines).
  2. Pack pieces into chunks of ~CHUNK_SIZE chars with CHUNK_OVERLAP.
  3. Attach metadata: chunk_id, document_id, page_number, section, heading, topic.

Page attribution is approximate (char offsets mapped back to pages) —
good enough for citations without complex layout analysis.
"""
from __future__ import annotations

import re

from config.settings import settings
from models.schemas import Chunk, ParsedDocument
from utils.helpers import new_id


def create_chunks(
    doc: ParsedDocument,
    processed_text: str,
    doc_structure: dict | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    doc_structure = doc_structure or {}

    topics = doc_structure.get("topics", []) or []
    default_topic = topics[0] if topics else ""

    # Map char offsets -> page numbers using original page lengths.
    page_spans = _page_spans(doc)
    full_for_offsets = "\n\n".join(p.text for p in doc.pages)

    # Semantic split: headings / double newlines / single newlines / sentences.
    pieces = _semantic_split(processed_text or doc.full_text)

    chunks: list[Chunk] = []
    buf = ""
    buf_start = 0
    cursor = 0  # running offset in processed text
    headings = [p.heading for p in doc.pages]

    def flush(buffer: str, start: int) -> None:
        if not buffer.strip():
            return
        page_no = _offset_to_page(full_for_offsets, page_spans, start)
        heading = _nearest_heading(buffer, headings)
        section = _detect_section(buffer)
        chunks.append(
            Chunk(
                chunk_id=f"chunk_{len(chunks) + 1:03d}_{doc.document_id[:4]}",
                document_id=doc.document_id,
                text=buffer.strip(),
                page_number=page_no,
                section=section,
                heading=heading,
                topic=default_topic,
            )
        )

    for piece in pieces:
        if len(buf) + len(piece) + 2 <= chunk_size:
            if not buf:
                buf_start = cursor
            buf = f"{buf}\n\n{piece}" if buf else piece
        else:
            flush(buf, buf_start)
            # overlap: carry tail of previous buffer
            tail = buf[-chunk_overlap:] if chunk_overlap and buf else ""
            buf_start = cursor - len(tail)
            buf = f"{tail}\n\n{piece}" if tail else piece
        cursor += len(piece) + 2
    flush(buf, buf_start)
    return chunks


def _semantic_split(text: str) -> list[str]:
    # Split on blank lines first, then long single blocks get sentence-split.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    pieces: list[str] = []
    for b in blocks:
        if len(b) <= 1200:
            pieces.append(b)
        else:
            # sentence split for very long blocks
            sents = re.split(r"(?<=[.!?])\s+", b)
            cur = ""
            for s in sents:
                if len(cur) + len(s) < 1000:
                    cur = f"{cur} {s}".strip()
                else:
                    if cur:
                        pieces.append(cur)
                    cur = s
            if cur:
                pieces.append(cur)
    return pieces or [text]


def _page_spans(doc: ParsedDocument) -> list[tuple[int, int, int]]:
    spans = []
    offset = 0
    for p in doc.pages:
        spans.append((offset, offset + len(p.text), p.page_number))
        offset += len(p.text) + 2
    return spans


def _offset_to_page(full: str, spans: list[tuple[int, int, int]], offset: int) -> int:
    ratio = len(full) / max(offset + 1, 1)
    # processed text length may differ; use proportional mapping
    approx = int(offset)
    for start, end, page_no in spans:
        if start <= approx <= end:
            return page_no
    return spans[-1][2] if spans else 1


def _nearest_heading(text: str, headings: list[str]) -> str:
    low = text.lower()
    for h in headings:
        if h and h.lower() in low:
            return h
    first = text.strip().split("\n")[0] if text.strip() else ""
    return first[:80] if len(first) < 120 else ""


def _detect_section(text: str) -> str:
    m = re.search(r"(section\s+[A-Z0-9.\-]+|chapter\s+\d+|part\s+[IVX\d]+)", text, re.I)
    return m.group(1).strip() if m else ""
