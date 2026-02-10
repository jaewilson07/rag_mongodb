"""Logging configuration compatibility shim."""

import logging


def configure_logging(log_level: str = "INFO", use_colored: bool = True) -> None:
    """Initialize logging configuration (sync wrapper).

    This is a compatibility shim that provides a sync interface.
    For async logging setup, use setup_logging from mdrag.mdrag_logging.service_logging directly.
    """
    # Set up basic logging for CLI use
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


__all__ = ["configure_logging"]
