"""Engine factory implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine
from prepmd.exceptions import EngineError


class _SimpleEngine(Engine):
    def __init__(self, engine_name: str) -> None:
        self._name = engine_name

    @property
    def name(self) -> str:
        return self._name

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        return [
            f"# Engine: {self._name}",
            f"# Project: {config.project_name}",
            f"# Replicas: {config.simulation.replicas}",
        ]


class EngineFactory:
    """Create engine instances from configuration names."""

    _supported = {"amber", "gromacs", "namd", "charmm", "openmm"}

    @classmethod
    def create(cls, engine_name: str) -> Engine:
        normalized = engine_name.lower()
        if normalized not in cls._supported:
            raise EngineError(f"Unsupported engine: {engine_name}")
        return _SimpleEngine(normalized)
