"""Simulation planning abstract base classes."""

from abc import ABC, abstractmethod
from pathlib import Path

from prepmd.config.models import ProjectConfig


class SimulationPlan(ABC):
    """Abstract simulation plan."""

    @abstractmethod
    def build(self, output_root: Path, config: ProjectConfig) -> None:
        """Build a simulation plan on disk."""
