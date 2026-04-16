"""Simulation planning abstract base classes."""

from abc import ABC, abstractmethod
from pathlib import Path


class SimulationPlan(ABC):
    """Abstract simulation plan.

    Concrete implementations are responsible for constructing the full
    directory structure and any generated files required to run a
    molecular-dynamics simulation project.
    """

    @abstractmethod
    def build(self) -> Path:
        """Build the simulation plan on disk and return the root directory."""
