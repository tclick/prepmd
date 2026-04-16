"""Base configuration validator protocol."""

from abc import ABC, abstractmethod

from prepmd.config.models import ProjectConfig


class BaseValidator(ABC):
    """Abstract config validator."""

    @abstractmethod
    def validate(self, config: ProjectConfig) -> None:
        """Raise if config is invalid."""
