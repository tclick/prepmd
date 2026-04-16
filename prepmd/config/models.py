"""Pydantic models for prepmd project configuration."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class EngineName(StrEnum):
    """Supported MD simulation engine identifiers."""

    AMBER = "amber"
    GROMACS = "gromacs"
    NAMD = "namd"
    CHARMM = "charmm"
    OPENMM = "openmm"


EnsembleType = Literal["NVT", "NPT", "NVE"]


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


class ProjectConfig(BaseModel):
    """Top-level project configuration."""

    project_name: str
    output_dir: str = "."
    protein: ProteinConfig = Field(default_factory=ProteinConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    engine: EngineConfig = Field(default_factory=EngineConfig)
