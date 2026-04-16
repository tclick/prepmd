"""Engine factory with entry-points plugin registry."""

from importlib.metadata import entry_points

from prepmd.config.models import EngineName, ProjectConfig
from prepmd.engines.amber import AmberEngine
from prepmd.engines.base import Engine
from prepmd.engines.charmm import CharmmEngine
from prepmd.engines.gromacs import GromacsEngine
from prepmd.engines.namd import NamdEngine
from prepmd.engines.openmm import OpenmmEngine
from prepmd.exceptions import EngineError

_BUILTIN_ENGINE_REGISTRY: dict[str, type[Engine]] = {
    EngineName.AMBER: AmberEngine,
    EngineName.GROMACS: GromacsEngine,
    EngineName.NAMD: NamdEngine,
    EngineName.CHARMM: CharmmEngine,
    EngineName.OPENMM: OpenmmEngine,
}


def _build_engine_registry() -> dict[str, type[Engine]]:
    """Build the engine registry, merging built-ins with any installed plugins.

    Third-party packages may register engines via the ``prepmd.engines``
    entry-points group.  Plugin entries override built-ins of the same name.
    """
    registry: dict[str, type[Engine]] = dict(_BUILTIN_ENGINE_REGISTRY)
    for ep in entry_points(group="prepmd.engines"):
        loaded: type[Engine] = ep.load()
        registry[ep.name] = loaded
    return registry


class EngineFactory:
    """Create engine instances by name.

    Engines are resolved from the combined built-in and plugin registry.
    Third-party packages may extend the available engines by registering
    under the ``prepmd.engines`` entry-points group in their package metadata.
    """

    @classmethod
    def create(cls, engine_name: str | EngineName) -> Engine:
        """Return an engine instance for *engine_name*.

        Parameters
        ----------
        engine_name:
            Case-insensitive engine identifier (e.g. ``"amber"``).

        Raises
        ------
        EngineError
            When *engine_name* is not found in the registry.
        """
        normalized = str(engine_name).lower()
        registry = _build_engine_registry()
        if normalized not in registry:
            raise EngineError(f"Unsupported engine: {engine_name!r}.  Available: {sorted(registry)}")
        return registry[normalized]()


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
