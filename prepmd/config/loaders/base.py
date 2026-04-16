"""Base configuration loader abstraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseConfigLoader(ABC):
    """Load raw configuration content from a file."""

    @abstractmethod
    def load(self, path: Path) -> dict[str, Any]:
        """Load config file from path into dictionary."""
