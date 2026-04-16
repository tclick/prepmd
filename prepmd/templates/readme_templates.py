"""README templates for simulation directories."""

from prepmd.config.models import ProjectConfig


def render_replica_readme(config: ProjectConfig, variant: str, replica_num: str, engine_name: str) -> str:
    """Render per-replica README text."""

    pdb_input = config.protein.pdb_files.get(variant) or "input.pdb"
    return (
        f"# {config.project_name} / {variant} / replica_{replica_num}\n\n"
        f"- Engine: **{engine_name}**\n"
        f"- Force field: **{config.engine.force_field}**\n"
        f"- Water model: **{config.engine.water_model}**\n"
        f"- Input PDB: `{pdb_input}`\n"
        f"- Target temperature: **{config.simulation.temperature:.1f} K**\n"
        f"- Production runs: **{config.simulation.production_runs} x "
        f"{config.simulation.production_run_length_ns} ns**\n"
    )
