"""Water box geometry abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from math import sqrt

from prepmd.config.models import WaterBoxConfig, WaterBoxShape
from prepmd.exceptions import InvalidBoxDimensionsError


class BoxGeometry(ABC):
    """Abstract water-box geometry."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Geometry name."""

    @property
    @abstractmethod
    def dimensions(self) -> tuple[float, float, float]:
        """Orthogonal x/y/z dimensions in Å."""

    @property
    @abstractmethod
    def volume(self) -> float:
        """Volume in Å³."""

    @property
    @abstractmethod
    def surface_area(self) -> float:
        """Surface area in Å²."""

    @abstractmethod
    def get_box_params(self) -> dict[str, str | float | tuple[float, float, float]]:
        """Return geometry-specific box parameters."""

    def validate_dimensions(self) -> None:
        """Validate positive dimensions."""
        if any(value <= 0.0 for value in self.dimensions):
            raise InvalidBoxDimensionsError(f"Box dimensions must be positive: {self.dimensions!r}")

    def generate_pdb_remarks(self) -> list[str]:
        """Return PDB REMARK lines describing the geometry."""
        x, y, z = self.dimensions
        return [
            f"REMARK PREPMD BOX_SHAPE {self.name}",
            f"REMARK PREPMD BOX_DIMENSIONS {x:.3f} {y:.3f} {z:.3f}",
            f"REMARK PREPMD BOX_VOLUME {self.volume:.3f}",
            f"REMARK PREPMD BOX_SURFACE_AREA {self.surface_area:.3f}",
        ]


class CubicBox(BoxGeometry):
    """Cubic box geometry."""

    def __init__(self, side_length: float) -> None:
        self.side_length = side_length
        self.validate_dimensions()

    @property
    def name(self) -> str:
        return WaterBoxShape.CUBIC

    @property
    def dimensions(self) -> tuple[float, float, float]:
        return (self.side_length, self.side_length, self.side_length)

    @property
    def volume(self) -> float:
        return self.side_length**3

    @property
    def surface_area(self) -> float:
        return 6.0 * (self.side_length**2)

    def get_box_params(self) -> dict[str, str | float | tuple[float, float, float]]:
        return {"shape": self.name, "side_length": self.side_length, "dimensions": self.dimensions}


class TruncatedOctahedronBox(BoxGeometry):
    """Truncated octahedron geometry."""

    def __init__(self, edge_length: float) -> None:
        self.edge_length = edge_length
        self.validate_dimensions()

    @property
    def name(self) -> str:
        return WaterBoxShape.TRUNCATED_OCTAHEDRON

    @property
    def dimensions(self) -> tuple[float, float, float]:
        bounding = 2.0 * self.edge_length
        return (bounding, bounding, bounding)

    @property
    def volume(self) -> float:
        return 8.0 * sqrt(2.0) * (self.edge_length**3)

    @property
    def surface_area(self) -> float:
        return 6.0 * (1.0 + (2.0 * sqrt(3.0))) * (self.edge_length**2)

    def get_box_params(self) -> dict[str, str | float | tuple[float, float, float]]:
        return {"shape": self.name, "edge_length": self.edge_length, "dimensions": self.dimensions}


class OrthorhombicBox(BoxGeometry):
    """Orthorhombic box geometry."""

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.validate_dimensions()

    @property
    def name(self) -> str:
        return WaterBoxShape.ORTHORHOMBIC

    @property
    def dimensions(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @property
    def volume(self) -> float:
        return self.x * self.y * self.z

    @property
    def surface_area(self) -> float:
        return 2.0 * ((self.x * self.y) + (self.x * self.z) + (self.y * self.z))

    def get_box_params(self) -> dict[str, str | float | tuple[float, float, float]]:
        return {"shape": self.name, "dimensions": self.dimensions}


def build_box_geometry(water_box: WaterBoxConfig) -> BoxGeometry:
    """Build a concrete geometry from water-box config."""
    if water_box.shape == WaterBoxShape.CUBIC:
        if water_box.side_length is None:
            raise InvalidBoxDimensionsError("Cubic boxes require side_length.")
        return CubicBox(side_length=water_box.side_length)
    if water_box.shape == WaterBoxShape.TRUNCATED_OCTAHEDRON:
        if water_box.edge_length is None:
            raise InvalidBoxDimensionsError("Truncated octahedrons require edge_length.")
        return TruncatedOctahedronBox(edge_length=water_box.edge_length)
    if water_box.dimensions is None:
        raise InvalidBoxDimensionsError("Orthorhombic boxes require dimensions.")
    x, y, z = water_box.dimensions
    return OrthorhombicBox(x=x, y=y, z=z)
