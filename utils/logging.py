"""Shared logging helper: console logging for developers, clean UI errors for users."""
from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

_configured = False

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def get_logger(name: str = "doc_platform") -> logging.Logger:
    global _configured
    logger = logging.getLogger(name)
    if not _configured:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        _configured = True
    return logger


def persist_error(context: str, exc: BaseException) -> str:
    """Append full traceback to logs/last_error.log; returns the file path.

    Screen messages are short by design — this file keeps the evidence
    needed to actually fix a failure.
    """
    LOG_DIR.mkdir(exist_ok=True)
    path = LOG_DIR / "last_error.log"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n{'=' * 70}\n{stamp} | {context}\n"
        f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    )
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass
    return str(path)


def persist_info(context: str, detail: str) -> None:
    """Append a one-line success/info record to logs/app.log."""
    try:
        LOG_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_DIR / "app.log", "a", encoding="utf-8") as f:
            f.write(f"{stamp} | {context} | {detail}\n")
    except Exception:
        pass
