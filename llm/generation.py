"""LLM generation with validation -> repair/regenerate loop.

    generate_response(context, spec, ...)  ->  final text
Handles: build prompt -> LLM call -> validate -> repair (max MAX_RETRIES).
"""
from __future__ import annotations

from config.settings import settings
from models.schemas import RequirementSpec, RetrievedChunk
from prompts.engine import build_prompt
from utils.logging import get_logger
from validation.output_validator import validate_output

log = get_logger(__name__)


def generate_response(
    context_chunks: list[RetrievedChunk],
    spec: RequirementSpec,
    llm_client,
    doc_structure: dict | None = None,
    temperature: float = 0.3,
    model: str | None = None,
) -> tuple[str, str, dict]:
    """Returns (final_text, prompt_used, validation_dict).

    `model` is the auto-selected id from llm/model_selector.select_llm()
    (passed by the pipeline). When None, the client uses the default.
    Raises RuntimeError if LLM unavailable or all attempts fail validation.
    """
    if llm_client is None or not llm_client.available:
        raise RuntimeError("LLM is not configured. Set OPENROUTER_API_KEY in .env.")
    prompt = build_prompt(spec, context_chunks, doc_structure)
    last_text = ""
    last_validation: dict = {}
    attempts = max(1, settings.max_retries)
    for attempt in range(1, attempts + 1):
        if attempt == 1:
            messages = [{"role": "user", "content": prompt}]
        else:
            # Repair pass: show previous output + issues, ask for fix.
            issues = "; ".join(last_validation.get("issues", []) or ["improve answer"])
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": last_text},
                {
                    "role": "user",
                    "content": (
                        f"The previous answer had these problems: {issues}. "
                        "Fix them. Use ONLY the provided document context. "
                        "Return the corrected answer in the requested format."
                    ),
                },
            ]
        text = llm_client.chat(
            messages=messages, temperature=temperature, max_tokens=2500, model=model
        )
        last_text = text
        result = validate_output(text, spec, context_chunks)
        last_validation = {
            "is_valid": result.is_valid, "issues": result.issues, "checks": result.checks,
            "attempts": attempt, "model": model or getattr(llm_client, "last_model_used", ""),
        }
        if result.is_valid:
            return text, prompt, last_validation
        log.info("Generation attempt %d failed validation: %s", attempt, result.issues)
    # Return best effort after exhausting retries (UI flags it).
    return last_text, prompt, last_validation
