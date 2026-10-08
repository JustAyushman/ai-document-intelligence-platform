"""Targeted-retrieval prompt template (assembled by prompts/engine.py)."""
RETRIEVAL_SYSTEM = (
    "Return only information relevant to the requested topic/section/year. "
    "Include [page N] citations; say 'Not found' if nothing is relevant."
)
