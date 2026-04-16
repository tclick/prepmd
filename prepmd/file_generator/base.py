"""Base classes for file generators."""

from abc import ABC, abstractmethod

from prepmd.config.models import ProjectConfig


class FileGenerator(ABC):
    """Base class for simulation input generators."""

    @abstractmethod
    def render(self, config: ProjectConfig) -> str:
        """Render text file content from config."""
