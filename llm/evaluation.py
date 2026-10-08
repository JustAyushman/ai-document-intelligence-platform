"""LLM-based quality evaluation (relevance, consistency, factuality, ...).

Deterministic heuristics are used when the LLM is unavailable.
"""
from __future__ import annotations

import json
import re

from models.schemas import QualityReport, RequirementSpec, RetrievedChunk
from utils.helpers import safe_truncate
from utils.logging import get_logger

log = get_logger(__name__)

EVAL_PROMPT = """You evaluate an AI answer against its source context.
Score 0-100 for: relevance, consistency, factuality, completeness, format_compliance.
Return JSON only: {"relevance": n, "consistency": n, "factuality": n, "completeness": n, "format_compliance": n, "notes": "<one line>"}.

USER REQUEST: %s
EXPECTED FORMAT: %s

SOURCE CONTEXT:
%s

ANSWER:
%s
"""


def evaluate_quality(
    answer: str,
    spec: RequirementSpec,
    context_chunks: list[RetrievedChunk],
    llm_client=None,
) -> QualityReport:
    if llm_client is not None and llm_client.available:
        try:
            context = safe_truncate(
                "\n---\n".join(c.chunk.text for c in context_chunks[:5]), 3000
            )
            raw = llm_client.chat(
                messages=[{
                    "role": "user",
                    "content": EVAL_PROMPT % (
                        spec.rewritten_query or spec.target,
                        spec.output_format,
                        context,
                        safe_truncate(answer, 3000),
                    ),
                }],
                json_mode=True, temperature=0.1, max_tokens=500,
            )
            data = json.loads(raw)
            return QualityReport(
                relevance=int(data.get("relevance", 0)),
                consistency=int(data.get("consistency", 0)),
                factuality=int(data.get("factuality", 0)),
                completeness=int(data.get("completeness", 0)),
                format_compliance=int(data.get("format_compliance", 0)),
                notes=str(data.get("notes", "")),
            )
        except Exception as exc:
            log.warning("LLM evaluation failed, using heuristic: %s", exc)
    return _heuristic_evaluate(answer, spec, context_chunks)


def _heuristic_evaluate(
    answer: str, spec: RequirementSpec, context_chunks: list[RetrievedChunk]
) -> QualityReport:
    """Cheap deterministic proxy — clearly labeled as heuristic in notes."""
    words = re.findall(r"\w+", answer.lower())
    vocab = set(words)
    relevance = 70 if len(answer.strip()) > 50 else 40
    if spec.target:
        keywords = [w for w in re.findall(r"\w+", spec.target.lower()) if len(w) > 3]
        hit = sum(1 for k in keywords if k in vocab)
        if keywords:
            relevance = min(95, 50 + int(45 * hit / len(keywords)))
    ctx_words: set[str] = set()
    for rc in context_chunks:
        ctx_words.update(re.findall(r"\w+", rc.chunk.text.lower()))
    overlap = len(vocab & ctx_words) / max(len(vocab), 1)
    factuality = min(90, int(50 + overlap * 60))
    consistency = 80 if answer.strip() else 20
    completeness = 75 if len(words) > 60 else 55
    fmt_ok = 85
    if spec.output_format == "json":
        try:
            json.loads(answer)
            fmt_ok = 95
        except Exception:
            fmt_ok = 45
    return QualityReport(
        relevance=relevance, consistency=consistency, factuality=factuality,
        completeness=completeness, format_compliance=fmt_ok,
        notes="Heuristic score (LLM unavailable).",
    )
