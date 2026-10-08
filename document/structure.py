"""LLM document understanding: semantic structure + topics + metadata.

Python orchestrates; the LLM interprets. Result is a flexible dict —
never a hard-coded schema — so any document type fits.
"""
from __future__ import annotations

import json

from models.schemas import ParsedDocument
from utils.helpers import safe_truncate
from utils.logging import get_logger

log = get_logger(__name__)

STRUCTURE_PROMPT = """Analyze this document sample and return JSON describing its semantic structure.
Be generic — this could be any document type (report, paper, manual, question paper, ...).
Return JSON with keys:
{
  "document_type": "<your best guess, e.g. report / question_paper / manual / article / other>",
  "summary": "<2-3 sentence overview>",
  "topics": ["<main topics>"],
  "sections": [{"name": "<section>", "description": "<what it covers>"}],
  "entities": ["<key entities>"],
  "suggested_metadata": {"<field>": "<why useful for retrieval>"}
}
Only return JSON, no other text.

DOCUMENT SAMPLE:
"""


def understand_document(doc: ParsedDocument, llm_client=None) -> dict:
    fallback = {
        "document_type": doc.file_type,
        "summary": f"{doc.file_name}: {doc.page_count} page(s) extracted.",
        "topics": [],
        "sections": [
            {"name": p.heading or f"Page {p.page_number}", "description": p.section}
            for p in doc.pages[:10]
        ],
        "entities": [],
        "suggested_metadata": {},
        "_source": "fallback",
    }
    if llm_client is None or not llm_client.available:
        return fallback
    try:
        sample = safe_truncate(doc.full_text, 5000)
        raw = llm_client.chat(
            messages=[{"role": "user", "content": STRUCTURE_PROMPT + sample}],
            json_mode=True, temperature=0.2, max_tokens=1500,
        )
        data = json.loads(raw)
        data["_source"] = "llm"
        # Normalize: guarantee expected keys exist.
        data.setdefault("document_type", doc.file_type)
        data.setdefault("topics", [])
        data.setdefault("sections", [])
        data.setdefault("entities", [])
        data.setdefault("summary", "")
        return data
    except Exception as exc:
        log.warning("LLM document understanding failed, using fallback: %s", exc)
        return fallback
