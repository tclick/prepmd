"""README templates for simulation directories."""

from importlib.resources import files

from prepmd.config.models import ProjectConfig

REPLICA_README_TEMPLATE = files("prepmd.resources").joinpath("replica_readme.md.tmpl").read_text(encoding="utf-8")


def render_replica_readme(config: ProjectConfig, variant: str, replica_num: str, engine_name: str) -> str:
    """Render per-replica README text."""

    pdb_input = config.protein.pdb_files.get(variant) or config.protein.pdb_file
    if pdb_input is None:
        variant_pdb_id = config.protein.pdb_ids.get(variant) or config.protein.pdb_id
        if variant_pdb_id is not None:
            pdb_input = f"PDB ID: {variant_pdb_id}"
    if pdb_input is None:
        pdb_input = "input.pdb"
    return REPLICA_README_TEMPLATE.format(
        project_name=config.project_name,
        variant=variant,
        replica_num=replica_num,
        engine_name=engine_name,
        force_field=config.engine.force_field,
        water_model=config.engine.water_model,
        pdb_input=pdb_input,
        temperature=config.simulation.temperature,
        production_runs=config.simulation.production_runs,
        production_run_length_ns=config.simulation.production_run_length_ns,
    )
