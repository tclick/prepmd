"""Engine protocols and abstractions."""

from abc import ABC, abstractmethod

from prepmd.config.models import ProjectConfig


class Engine(ABC):
    """Abstract simulation engine interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""

    @abstractmethod
    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        """Generate engine-specific input script content."""
