"""README templates for simulation directories."""

from prepmd.config.models import ProjectConfig


def render_replica_readme(config: ProjectConfig, variant: str, replica_num: str, engine_name: str) -> str:
    """Render per-replica README text."""

    pdb_input = config.protein.pdb_files.get(variant) or config.protein.pdb_file
    if pdb_input is None and config.protein.pdb_id is not None:
        pdb_input = f"PDB ID: {config.protein.pdb_id}"
    if pdb_input is None:
        pdb_input = "input.pdb"
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
