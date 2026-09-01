"""Session log file setup. Errors and skipped rows go here, never to the UI."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".nfl_draft_analyzer" / "logs"

_configured = False


def get_logger() -> logging.Logger:
    global _configured
    logger = logging.getLogger("nfl_draft_analyzer")
    if _configured:
        return logger

    logger.setLevel(logging.DEBUG)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"session_{datetime.now():%Y%m%d_%H%M%S}.log"
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())

    _configured = True
    return logger
