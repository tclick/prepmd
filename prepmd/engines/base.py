"""Engine protocols and abstractions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from prepmd.config.models import ProjectConfig
from prepmd.core.box_geometry import BoxGeometry, build_box_geometry
from prepmd.exceptions import BoxShapeNotSupportedError


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    """Static metadata describing what an engine supports."""

    supported_ensembles: frozenset[str]
    supported_box_shapes: frozenset[str]
    supported_water_models: frozenset[str] | None = None
    supported_force_fields: frozenset[str] | None = None


class Engine(ABC):
    """Abstract simulation engine interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""

    @property
    @abstractmethod
    def capabilities(self) -> EngineCapabilities:
        """Static capability metadata for this engine."""

    @property
    def supported_box_shapes(self) -> set[str]:
        """Set of native water-box shapes supported by this engine."""
        return set(self.capabilities.supported_box_shapes)

    @abstractmethod
    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        """Generate engine-specific input script content."""

    @abstractmethod
    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        """Render engine-specific preparation instructions from a PDB input."""

    def supports_box_shape(self, shape: str) -> bool:
        """Return whether *shape* is supported by this engine."""
        return shape in self.supported_box_shapes

    def get_box_geometry(self, config: ProjectConfig) -> BoxGeometry:
        """Build and validate water-box geometry for this engine."""
        shape = config.water_box.shape
        if not self.supports_box_shape(shape):
            raise BoxShapeNotSupportedError(f"Engine {self.name} does not support box shape {shape!r}.")
        return build_box_geometry(config.water_box)

    def get_box_params(self, config: ProjectConfig) -> dict[str, str | float | tuple[float, float, float]]:
        """Return engine-ready geometry parameters."""
        return self.get_box_geometry(config).get_box_params()

    def get_cutoff_spacing(self, config: ProjectConfig) -> tuple[float, float]:
        """Estimate default cutoff and spacing from geometry dimensions."""
        geometry = self.get_box_geometry(config)
        min_dimension = min(geometry.dimensions)
        cutoff = max((min_dimension / 2.0) - 1.0, 0.1)
        spacing = max(cutoff / 10.0, 0.1)
        return cutoff, spacing
