"""Document identification: file extension -> parser choice.

Deliberately simple — Python handles routing, the LLM handles meaning.
"""
from __future__ import annotations

from pathlib import Path

EXTENSION_TO_TYPE = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",  # python-docx handles most .doc; legacy binary .doc may fail gracefully
    ".txt": "txt",
    ".md": "txt",
}

SUPPORTED = set(EXTENSION_TO_TYPE.keys())


def identify_document(file_name: str) -> dict:
    """Return {'file_type': ..., 'parser': ..., 'supported': bool}."""
    ext = Path(file_name).suffix.lower()
    file_type = EXTENSION_TO_TYPE.get(ext, "unknown")
    return {
        "extension": ext,
        "file_type": file_type,
        "parser": f"{file_type}_parser" if file_type != "unknown" else "unsupported",
        "supported": ext in SUPPORTED,
    }
