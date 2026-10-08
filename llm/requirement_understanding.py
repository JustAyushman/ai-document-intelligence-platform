"""Thin wrappers: document-understanding + requirement-understanding live
with the LLM because they are semantic tasks (see design principle)."""
from __future__ import annotations

import json

from models.schemas import RequirementSpec
from utils.logging import get_logger

log = get_logger(__name__)

REQUIREMENT_PROMPT = """Interpret the user's request about a document.
Return JSON only:
{
  "intent": "one of: summarize | extract | classify | retrieve | generate | custom",
  "target": "<what the user wants, e.g. 'AI-related questions'>",
  "scope": "<which part of the document, e.g. 'whole document' or 'section about AI'>",
  "output_format": "one of: markdown | bullets | table | json | plain",
  "constraints": ["<any explicit constraints like years, sections, fields to preserve>"],
  "rewritten_query": "<optimized retrieval query capturing the semantic need>"
}

TASK HINT: %s

USER REQUEST:
%s
"""

INTENT_HINTS = {
    "summarize": "The user wants a summary.",
    "extract": "The user wants structured extraction.",
    "classify": "The user wants classification.",
    "retrieve": "The user wants to find specific information.",
    "generate": "The user wants new content grounded in the document.",
    "custom": "General request; infer the best intent.",
}


def understand_requirement(
    user_text: str, task_hint: str = "custom", llm_client=None
) -> RequirementSpec:
    """LLM interprets the requirement; keyword fallback if LLM unavailable."""
    spec = _keyword_fallback(user_text, task_hint)
    if llm_client is None or not llm_client.available:
        return spec
    try:
        hint = INTENT_HINTS.get(task_hint, INTENT_HINTS["custom"])
        raw = llm_client.chat(
            messages=[{"role": "user", "content": REQUIREMENT_PROMPT % (hint, user_text)}],
            json_mode=True, temperature=0.2, max_tokens=600,
        )
        data = json.loads(raw)
        return RequirementSpec(
            intent=str(data.get("intent", spec.intent)),
            target=str(data.get("target", user_text)),
            scope=str(data.get("scope", "current document")),
            output_format=str(data.get("output_format", "markdown")),
            constraints=list(data.get("constraints", [])),
            rewritten_query=str(data.get("rewritten_query", user_text)),
        )
    except Exception as exc:
        log.warning("Requirement understanding fell back to keywords: %s", exc)
        return spec


def _keyword_fallback(user_text: str, task_hint: str) -> RequirementSpec:
    t = user_text.lower()
    if task_hint != "custom":
        intent = task_hint
    elif any(w in t for w in ("summar", "tldr", "overview")):
        intent = "summarize"
    elif any(w in t for w in ("extract", "list all", "find all", "dates", "entities")):
        intent = "extract"
    elif "classif" in t:
        intent = "classify"
    elif any(w in t for w in ("find", "give me", "related to", "about", "where", "which")):
        intent = "retrieve"
    elif any(w in t for w in ("write", "generate", "create", "draft", "explain")):
        intent = "generate"
    else:
        intent = "custom"
    fmt = "table" if intent == "extract" else ("bullets" if intent == "retrieve" else "markdown")
    return RequirementSpec(
        intent=intent, target=user_text, scope="current document",
        output_format=fmt, constraints=[], rewritten_query=user_text,
    )
