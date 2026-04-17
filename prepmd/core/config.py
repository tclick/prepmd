"""Core configuration models."""

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class CoreSimulationConfig:
    """Core configuration for protocol rendering.

    Parameters
    ----------
    target_temperature : float
        Target temperature in Kelvin.
    production_runs : int
        Number of production segments.
    production_run_length_ns : int
        Length of each production segment in nanoseconds.
    force_field : str
        Force field name.
    water_model : str
        Water model name.
    """

    target_temperature: float = 300.0
    production_runs: int = 3
    production_run_length_ns: int = 100
    force_field: str = "ff19sb"
    water_model: str = "OPC3"
    minimization_restraints: tuple[float, float, float] = field(default_factory=lambda: (10.0, 5.0, 0.0))
    equilibration_restraints: tuple[float, float, float, float, float] = field(
        default_factory=lambda: (5.0, 2.0, 1.0, 0.1, 0.0)
    )
