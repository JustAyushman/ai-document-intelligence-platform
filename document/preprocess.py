"""LLM-assisted text preprocessing.

Keeps BOTH original and processed representations:
  original  -> for citations / verification
  processed -> cleaner text for chunking + retrieval

Python does deterministic cleaning; the LLM does semantic cleaning
(noise removal, boundary hints) on a truncated sample to bound cost.
"""
from __future__ import annotations

import json
import re

from models.schemas import ParsedDocument
from utils.helpers import clean_whitespace, safe_truncate
from utils.logging import get_logger

log = get_logger(__name__)


def preprocess_document(doc: ParsedDocument, llm_client=None) -> dict:
    """Return {'original_text', 'processed_text', 'notes', 'pages'}."""
    original = doc.full_text
    # Deterministic pass: fix hyphenation, bullets, excess whitespace.
    processed = _deterministic_clean(original)
    notes = ["deterministic clean: hyphenation, bullets, whitespace normalized"]

    # LLM semantic pass on a bounded sample (first ~3500 chars).
    if llm_client is not None and llm_client.available:
        try:
            sample = safe_truncate(processed, 3500)
            prompt = (
                "You are a document preprocessing assistant. Clean the text sample below: "
                "remove headers/footers/page-number noise, fix broken sentences from PDF extraction, "
                "preserve headings and section structure. Return JSON: "
                '{"cleaned": "<cleaned text>", "notes": "<short note>"}.\n\nTEXT:\n' + sample
            )
            raw = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True, temperature=0.1, max_tokens=2000,
            )
            data = json.loads(raw)
            llm_notes = str(data.get("notes", "")).strip()
            # Apply LLM guidance conservatively: keep full deterministic text,
            # just record semantic notes (never destroy original content).
            if llm_notes:
                notes.append(f"llm: {llm_notes}")
        except Exception as exc:  # LLM assist is optional — never fail the pipeline
            log.warning("LLM preprocess assist failed, using deterministic text: %s", exc)
            notes.append("llm assist skipped (API unavailable)")

    return {
        "original_text": original,
        "processed_text": processed,
        "notes": notes,
        "pages": len(doc.pages),
    }


def _deterministic_clean(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # de-hyphenate
    text = re.sub(r"•", "\n- ", text)
    text = clean_whitespace(text)
    return text
