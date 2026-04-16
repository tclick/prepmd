"""Pydantic models for prepmd project configuration."""

from pydantic import BaseModel, Field


class ProteinConfig(BaseModel):
    """Protein-level simulation variants."""

    variants: list[str] = Field(default_factory=lambda: ["wild_type"])


class SimulationConfig(BaseModel):
    """Simulation execution options."""

    replicas: int = Field(default=1, ge=1)
    temperature: float = Field(default=300.0, gt=0.0)
    ensemble: str = Field(default="NVT")


class EngineConfig(BaseModel):
    """Engine selection and options."""

    name: str = "amber"
    options: dict[str, str] = Field(default_factory=dict)


class ProjectConfig(BaseModel):
    """Top-level project configuration."""

    project_name: str
    output_dir: str = "."
    protein: ProteinConfig = Field(default_factory=ProteinConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    engine: EngineConfig = Field(default_factory=EngineConfig)
