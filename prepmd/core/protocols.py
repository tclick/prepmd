"""Protocol definitions and defaults."""

from dataclasses import dataclass

from prepmd.core.config import CoreSimulationConfig


@dataclass(slots=True)
class ProtocolStage:
    """Single simulation protocol stage descriptor."""

    name: str
    restraints_kcal_per_a2: float
    notes: str


def get_default_protocol(config: CoreSimulationConfig) -> dict[str, list[ProtocolStage]]:
    """Build the default simulation protocol stack."""

    minimization = [
        ProtocolStage("01_full_restraint", config.minimization_restraints[0], "Protein heavy atoms restrained"),
        ProtocolStage("02_backbone_restraint", config.minimization_restraints[1], "Backbone restrained"),
        ProtocolStage("03_no_restraint", config.minimization_restraints[2], "No positional restraints"),
    ]
    heating = [ProtocolStage("02_heating", 5.0, f"NVT heating from 0 K to {config.target_temperature:.1f} K")]
    equilibration_labels = ["01_5kcal", "02_2kcal", "03_1kcal", "04_0.1kcal", "05_0kcal"]
    equilibration = [
        ProtocolStage(label, value, "NPT tapered equilibration")
        for label, value in zip(equilibration_labels, config.equilibration_restraints, strict=True)
    ]
    production = [
        ProtocolStage(
            f"run_{run_idx:03d}",
            0.0,
            f"{config.production_run_length_ns}-ns production segment",
        )
        for run_idx in range(1, config.production_runs + 1)
    ]
    return {
        "01_minimization": minimization,
        "02_heating": heating,
        "03_equilibration": equilibration,
        "04_production": production,
    }
