"""Pydantic models for prepmd project configuration."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EngineName(StrEnum):
    """Supported MD simulation engine identifiers."""

    AMBER = "amber"
    GROMACS = "gromacs"
    NAMD = "namd"
    CHARMM = "charmm"
    OPENMM = "openmm"


class WaterBoxShape(StrEnum):
    """Supported water box geometries."""

    CUBIC = "cubic"
    TRUNCATED_OCTAHEDRON = "truncated_octahedron"
    ORTHORHOMBIC = "orthorhombic"


type EnsembleType = Literal["NVT", "NPT", "NVE"]


class ProteinConfig(BaseModel):
    """Protein-level simulation variants.

    Parameters
    ----------
    variants : list[str]
        Names of protein variants to prepare (for example: ``apo`` and ``holo``).
    pdb_files : dict[str, str | None]
        Optional mapping of variant name to the variant-specific input PDB path.
    """

    variants: list[str] = Field(default_factory=lambda: ["apo", "holo"])
    pdb_files: dict[str, str | None] = Field(default_factory=dict)
    pdb_file: str | None = None
    pdb_id: str | None = None
    pdb_cache_dir: str | None = None
    offline: bool = False

    @model_validator(mode="after")
    def validate_pdb_inputs(self) -> "ProteinConfig":
        """Reject ambiguous PDB input at model-validation time.

        Only the mutually exclusive "both set" case is checked here so that
        partial construction (e.g. ``ProteinConfig()`` used as a default factory
        or assembled incrementally via CLI merging) stays valid until the full
        :class:`prepmd.config.validators.pipeline.ValidationPipeline` runs.
        """
        has_variant_local = any(path for path in self.pdb_files.values() if path)
        has_local = self.pdb_file is not None or has_variant_local
        has_remote = self.pdb_id is not None
        if has_local and has_remote:
            raise ValueError("Specify either a local PDB file or a PDB ID, not both.")
        return self


class SimulationConfig(BaseModel):
    """Simulation execution options.

    Parameters
    ----------
    replicas : int
        Number of independent replicas for each variant.
    temperature : float
        Target temperature (K) used for NVT heating.
    ensemble : EnsembleType
        Production ensemble label (one of NVT, NPT, NVE).
    production_runs : int
        Number of 100-ns production run segments to generate.
    production_run_length_ns : int
        Duration in ns for each production run segment.
    """

    replicas: int = Field(default=1, ge=1)
    temperature: float = Field(default=300.0, gt=0.0)
    ensemble: EnsembleType = "NVT"
    production_runs: int = Field(default=3, ge=1)
    production_run_length_ns: int = Field(default=100, ge=1)


class EngineConfig(BaseModel):
    """Engine selection and options.

    Parameters
    ----------
    name : EngineName
        Simulation engine name (Amber, NAMD, Gromacs, CHARMM, OpenMM).
    force_field : str
        Selected force field (default: ``ff19sb``).
    water_model : str
        Selected water model (default: ``OPC3``).
    options : dict[str, str]
        Additional engine-specific options.
    """

    name: EngineName = EngineName.AMBER
    force_field: str = "ff19sb"
    water_model: str = "OPC3"
    options: dict[str, str] = Field(default_factory=dict)


class WaterBoxConfig(BaseModel):
    """Water-box geometry configuration."""

    shape: WaterBoxShape = WaterBoxShape.CUBIC
    side_length: float | None = None
    edge_length: float | None = None
    dimensions: tuple[float, float, float] | None = None
    auto_box_padding: float = Field(default=10.0, gt=0.0)

    @model_validator(mode="after")
    def validate_shape_dimensions(self) -> "WaterBoxConfig":
        """Validate and normalize shape-dependent dimensions."""
        if self.shape == WaterBoxShape.CUBIC:
            if self.edge_length is not None or self.dimensions is not None:
                raise ValueError("Cubic box only accepts side_length.")
            if self.side_length is None:
                self.side_length = self.auto_box_padding
            if self.side_length <= 0.0:
                raise ValueError("Cubic side_length must be positive.")
            return self

        if self.shape == WaterBoxShape.TRUNCATED_OCTAHEDRON:
            if self.side_length is not None or self.dimensions is not None:
                raise ValueError("Truncated octahedron only accepts edge_length.")
            if self.edge_length is None:
                self.edge_length = self.auto_box_padding
            if self.edge_length <= 0.0:
                raise ValueError("Truncated octahedron edge_length must be positive.")
            return self

        if self.side_length is not None or self.edge_length is not None:
            raise ValueError("Orthorhombic box only accepts dimensions.")
        if self.dimensions is None:
            self.dimensions = (self.auto_box_padding, self.auto_box_padding, self.auto_box_padding)
        if any(value <= 0.0 for value in self.dimensions):
            raise ValueError("Orthorhombic dimensions must all be positive.")
        return self


class ProjectConfig(BaseModel):
    """Top-level project configuration."""

    project_name: str
    output_dir: str = "."
    protein: ProteinConfig = Field(default_factory=ProteinConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    engine: EngineConfig = Field(default_factory=EngineConfig)
    water_box: WaterBoxConfig = Field(default_factory=WaterBoxConfig)
