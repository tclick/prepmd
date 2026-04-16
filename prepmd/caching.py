"""Caching and memoization helpers."""

from collections.abc import Callable
from functools import lru_cache
from typing import Any


def memoize(maxsize: int = 128) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Apply functools.lru_cache with configurable maxsize."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return lru_cache(maxsize=maxsize)(func)

    return decorator
