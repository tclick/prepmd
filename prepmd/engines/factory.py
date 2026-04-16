"""Engine factory implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.amber import AmberEngine
from prepmd.engines.base import Engine
from prepmd.engines.charmm import CharmmEngine
from prepmd.engines.gromacs import GromacsEngine
from prepmd.engines.namd import NamdEngine
from prepmd.engines.openmm import OpenmmEngine
from prepmd.exceptions import EngineError

_ENGINE_REGISTRY: dict[str, type[Engine]] = {
    "amber": AmberEngine,
    "gromacs": GromacsEngine,
    "namd": NamdEngine,
    "charmm": CharmmEngine,
    "openmm": OpenmmEngine,
}


class EngineFactory:
    """Create engine instances from configuration names."""

    _supported = set(_ENGINE_REGISTRY.keys())

    @classmethod
    def create(cls, engine_name: str) -> Engine:
        normalized = engine_name.lower()
        if normalized not in cls._supported:
            raise EngineError(f"Unsupported engine: {engine_name}")
        return _ENGINE_REGISTRY[normalized]()


def generate_engine_preview(config: ProjectConfig) -> list[str]:
    """Generate a short preview for engine files.

    Parameters
    ----------
    config : ProjectConfig
        Project-level simulation configuration.

    Returns
    -------
    list[str]
        Rendered engine preview lines.
    """

    engine = EngineFactory.create(config.engine.name)
    return engine.generate_inputs(config)
