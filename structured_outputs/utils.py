# utils.py
import logging
import sys

# ── Logger ────────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Return a consistently formatted logger for any pipeline module."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger


# ── Text helpers ───────────────────────────────────────────────────────────────

def truncate(text: str, max_chars: int = 120) -> str:
    """Truncate a string for safe log output."""
    text = text.strip()
    return text[:max_chars] + "…" if len(text) > max_chars else text
