"""Deterministic output validation (Python) + hooks for semantic checks.

Rule: Python validates what is deterministic (empty, format, length);
the LLM judges semantics (groundedness) in evaluation / regeneration.
"""
from __future__ import annotations

import json

from models.schemas import RequirementSpec, RetrievedChunk, ValidationResult


def validate_output(
    text: str,
    spec: RequirementSpec,
    context: list[RetrievedChunk],
) -> ValidationResult:
    issues: list[str] = []
    checks: dict = {}

    # 1. Non-empty
    checks["non_empty"] = bool(text and text.strip())
    if not checks["non_empty"]:
        issues.append("Output is empty.")

    # 2. Minimum substance
    words = len(text.split()) if text else 0
    checks["word_count"] = words
    if text and words < 10:
        issues.append("Output is too short to answer the request.")

    # 3. Format compliance (deterministic part)
    fmt_ok = True
    if spec.output_format == "json" and text.strip():
        try:
            json.loads(text)
        except Exception:
            # allow fenced ```json blocks
            inner = text.strip()
            if "```" in inner:
                try:
                    inner = inner.split("```")[1]
                    inner = inner.replace("json", "", 1).strip()
                    json.loads(inner)
                except Exception:
                    fmt_ok = False
                    issues.append("Requested JSON format but output is not valid JSON.")
            else:
                fmt_ok = False
                issues.append("Requested JSON format but output is not valid JSON.")
    elif spec.output_format == "table" and text.strip():
        if "|" not in text and "\t" not in text:
            fmt_ok = False
            issues.append("Requested table format but no table structure found.")
    checks["format_compliance"] = fmt_ok

    # 4. Groundedness proxy: at least some content words overlap the context.
    if context and text:
        import re

        ctx_vocab = set()
        for rc in context:
            ctx_vocab.update(re.findall(r"\w+", rc.chunk.text.lower()))
        ans_words = [w for w in re.findall(r"\w+", text.lower()) if len(w) > 3]
        overlap = sum(1 for w in set(ans_words) if w in ctx_vocab)
        ratio = overlap / max(len(set(ans_words)), 1)
        checks["context_overlap"] = round(ratio, 3)
        if ratio < 0.15 and len(ans_words) > 20:
            issues.append("Answer shares little vocabulary with retrieved context (possible hallucination).")
    else:
        checks["context_overlap"] = 0.0

    # 5. Refusal to hallucinate: if model says not found, that's valid.
    if text and "not found in document" in text.lower():
        checks["honest_abstention"] = True

    return ValidationResult(is_valid=not issues, issues=issues, checks=checks)
