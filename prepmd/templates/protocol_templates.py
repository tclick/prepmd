"""Simulation protocol text templates."""

from prepmd.config.models import ProjectConfig
from prepmd.core.config import CoreSimulationConfig
from prepmd.core.protocols import get_default_protocol


def render_protocol_overview(config: ProjectConfig) -> str:
    """Render protocol overview markdown."""

    core = CoreSimulationConfig(
        target_temperature=config.simulation.temperature,
        production_runs=config.simulation.production_runs,
        production_run_length_ns=config.simulation.production_run_length_ns,
        force_field=config.engine.force_field,
        water_model=config.engine.water_model,
    )
    sections = ["# Simulation Protocol Overview", ""]
    for phase, stages in get_default_protocol(core).items():
        sections.append(f"## {phase}")
        for stage in stages:
            sections.append(
                f"- **{stage.name}**: restraint={stage.restraints_kcal_per_a2:g} kcal/mol/Å²; {stage.notes}"
            )
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"
