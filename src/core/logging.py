"""Logging: console configuration (from logging_config)."""

from __future__ import annotations

import logging
import os
from typing import Optional


def configure_logging(log_level: Optional[str] = None) -> None:
    """Configure console logging for the application.

    Args:
        log_level: Optional log level override (e.g., "INFO", "DEBUG").
    """
    level_name = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )


__all__ = ["configure_logging"]
