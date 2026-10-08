"""Prompt engine: combines system + task + requirement + context + format.

Single place where final LLM prompts are assembled (transparent in UI).
"""
from __future__ import annotations

from models.schemas import RequirementSpec, RetrievedChunk
from prompts.fragments import (
    classification_instructions,
    custom_instructions,
    extraction_instructions,
    generation_instructions,
    retrieval_instructions,
    summarization_instructions,
)
from utils.helpers import safe_truncate

SYSTEM = (
    "You are a document intelligence assistant. Answer strictly from the "
    "DOCUMENT CONTEXT below. If the context lacks the answer, say so explicitly. "
    "Never invent page numbers, years, names, or numbers."
)


def build_prompt(
    spec: RequirementSpec,
    context: list[RetrievedChunk],
    doc_structure: dict | None = None,
) -> str:
    task_block = _task_block(spec)
    ctx_block = _context_block(context)
    struct = ""
    if doc_structure:
        dtype = doc_structure.get("document_type", "")
        topics = ", ".join(doc_structure.get("topics", [])[:8])
        struct = f"\nDOCUMENT OVERVIEW: type={dtype}; topics={topics}\n"
    fmt_note = f"\nREQUIRED OUTPUT FORMAT: {spec.output_format}"
    return (
        f"{SYSTEM}\n\n{task_block}{struct}\n"
        f"USER REQUIREMENT: {spec.rewritten_query or spec.target}\n"
        f"SCOPE: {spec.scope}{fmt_note}\n\n"
        f"DOCUMENT CONTEXT:\n{ctx_block}\n\n"
        "Now produce the answer with source citations like [page N] where possible."
    )


def _task_block(spec: RequirementSpec) -> str:
    builders = {
        "summarize": summarization_instructions,
        "extract": extraction_instructions,
        "classify": classification_instructions,
        "generate": generation_instructions,
        "retrieve": retrieval_instructions,
        "custom": custom_instructions,
    }
    fn = builders.get(spec.intent, custom_instructions)
    try:
        # extract takes (target, constraints, fmt)
        if spec.intent == "extract":
            return fn(spec.target, spec.constraints, spec.output_format)  # type: ignore
        return fn(spec.target, spec.constraints)  # type: ignore
    except TypeError:
        return custom_instructions(spec.target, spec.constraints)


def _context_block(context: list[RetrievedChunk]) -> str:
    parts = []
    for rc in context:
        c = rc.chunk
        label = f"[chunk {c.chunk_id} | page {c.page_number}"
        if c.section:
            label += f" | {c.section}"
        if c.heading:
            label += f" | {c.heading}"
        label += f" | score {rc.score:.2f}]"
        parts.append(f"{label}\n{safe_truncate(c.text, 1500)}")
    return "\n\n---\n\n".join(parts) if parts else "(no context retrieved)"
