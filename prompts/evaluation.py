"""Evaluation prompt template (used by llm/evaluation.py)."""
EVALUATION_SYSTEM = (
    "Score the answer 0-100 on relevance, consistency, factuality, "
    "completeness, format_compliance. Return JSON only."
)
