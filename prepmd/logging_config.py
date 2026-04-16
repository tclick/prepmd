"""Centralized loguru logging configuration."""

import sys

from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    """Configure application logging sinks and format."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    )
