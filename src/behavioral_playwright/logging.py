"""Structured logging utilities for behavioral-playwright."""

import logging
import sys
from typing import Optional


def configure_logging(
    level: int = logging.INFO,
    stream: Optional[object] = None,
    format_str: Optional[str] = None
) -> logging.Logger:
    """Configures and returns the root logger for behavioral-playwright."""
    if format_str is None:
        format_str = "%(asctime)s [%(levelname)s] (%(name)s) %(message)s"

    target_stream = stream or sys.stdout

    root_logger = logging.getLogger("behavioral_playwright")
    root_logger.setLevel(level)

    # Avoid duplicate handlers if already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler(target_stream)
        formatter = logging.Formatter(format_str, datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Returns a namespaced logger under behavioral_playwright."""
    if name.startswith("behavioral_playwright"):
        return logging.getLogger(name)
    return logging.getLogger(f"behavioral_playwright.{name}")


def log_resolution(
    logger: logging.Logger,
    target: str,
    strategy: str,
    candidates: int,
    confidence: float,
    success: bool,
    elapsed_ms: float,
    selector: Optional[str] = None
) -> None:
    """Logs structured self-healing resolution events."""
    logger.info(
        f"[Resolver] target='{target}' | strategy={strategy} | candidates={candidates} | "
        f"confidence={confidence:.2f} | success={success} | elapsed={elapsed_ms:.1f}ms | selector='{selector}'"
    )
