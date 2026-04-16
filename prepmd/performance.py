"""Small performance utilities."""

from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any

from loguru import logger


def profile(name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Log runtime for a wrapped function."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = perf_counter() - start
                logger.debug(f"{name or func.__name__} took {elapsed:.4f}s")

        return wrapper

    return decorator
