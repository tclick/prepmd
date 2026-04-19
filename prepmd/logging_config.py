"""Centralized loguru logging configuration."""

import sys
from typing import Literal

from loguru import logger


def configure_logging(level: str = "INFO", *, log_format: Literal["text", "json"] = "text") -> None:
    """Configure application logging sinks and format."""
    logger.remove()
    match log_format:
        case "json":
            logger.add(sys.stderr, level=level, serialize=True)
        case _:
            logger.add(
                sys.stderr,
                level=level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
            )
