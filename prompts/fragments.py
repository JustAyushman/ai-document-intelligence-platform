"""Task-specific prompt fragment builders (pure functions)."""
from __future__ import annotations


def summarization_instructions(target: str, constraints: list[str]) -> str:
    c = f"\nConstraints: {'; '.join(constraints)}" if constraints else ""
    return (
        "TASK: Summarize the provided context according to the user's requirement.\n"
        f"Focus: {target or 'the most important content'}.{c}\n"
        "Rules: use ONLY the context; do not invent facts; "
        "preserve section/page references where available."
    )


def extraction_instructions(target: str, constraints: list[str], fmt: str) -> str:
    c = f"\nConstraints: {'; '.join(constraints)}" if constraints else ""
    return (
        "TASK: Extract the requested information in a structured format.\n"
        f"Extract: {target}.{c}\n"
        f"Output format: {fmt}. Rules: every item must be traceable to the context; "
        "mark anything not found as 'Not found in document'."
    )


def classification_instructions(target: str, constraints: list[str]) -> str:
    c = f"\nCategories/constraints: {'; '.join(constraints)}" if constraints else ""
    return (
        "TASK: Classify the provided content according to the requested categories.\n"
        f"Classify with respect to: {target}.{c}\n"
        "Rules: assign each item exactly one label; give a one-line justification "
        "grounded in the context."
    )


def generation_instructions(target: str, constraints: list[str]) -> str:
    c = f"\nConstraints: {'; '.join(constraints)}" if constraints else ""
    return (
        "TASK: Generate new content using the retrieved document context.\n"
        f"Goal: {target}.{c}\n"
        "Rules: stay grounded in the context; clearly separate quoted facts "
        "from newly generated explanation."
    )


def retrieval_instructions(target: str, constraints: list[str]) -> str:
    c = f"\nMust preserve/consider: {'; '.join(constraints)}" if constraints else ""
    return (
        "TASK: Return only information relevant to the user's requested topic.\n"
        f"Topic: {target}.{c}\n"
        "Rules: quote or closely paraphrase the source; include "
        "[page N] / [section] citations; say 'Not found' if nothing is relevant."
    )


def custom_instructions(target: str, constraints: list[str]) -> str:
    c = f"\nConstraints: {'; '.join(constraints)}" if constraints else ""
    return (
        "TASK: Fulfil the user's custom request using the document context.\n"
        f"Request: {target}.{c}\n"
        "Rules: be helpful and grounded; do not add unsupported claims."
    )
