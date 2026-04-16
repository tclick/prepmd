"""Command line entrypoint."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from prepmd.cli.commands.setup import setup_project
from prepmd.config.loader import ConfigLoader
from prepmd.config.models import ProjectConfig
from prepmd.structure_builder.builder import StructureBuilder
from prepmd.utils.logging import configure_logging

LICENSE_TEXT = "GNU GPL-3.0-or-later"
SUPPORTED_ENGINES = ["amber", "namd", "gromacs", "charmm", "openmm"]
console = Console()
PROJECT_NAME_OPTIONAL = typer.Option(None, help="Project name.")
OUTPUT_DIR_OPTIONAL = typer.Option(None, help="Output directory.")
REPLICAS_OPTIONAL = typer.Option(None, min=1, help="Replicas per variant.")
TEMPERATURE_OPTIONAL = typer.Option(None, min=1.0, help="Target temperature in K.")
ENGINE_OPTIONAL = typer.Option(None, help=f"Engine name ({', '.join(SUPPORTED_ENGINES)}).")
FORCE_FIELD_OPTIONAL = typer.Option(None, help="Force field name.")
WATER_MODEL_OPTIONAL = typer.Option(None, help="Water model name.")
PRODUCTION_RUNS_OPTIONAL = typer.Option(None, min=1, help="Number of 100-ns production segments.")
APO_PDB_OPTION = typer.Option(None, help="Apo input PDB file.")
HOLO_PDB_OPTION = typer.Option(None, help="Holo input PDB file.")
CONFIG_OPTION = typer.Option(
    None,
    "--config",
    "-c",
    help="Optional YAML/TOML config file. CLI options override config values.",
)

app = typer.Typer(help="prepmd CLI")


@app.command("license")
def show_license() -> None:
    """Display project license."""
    console.print(f"[bold green]{LICENSE_TEXT}[/bold green]")


@app.command("setup")
def setup(config: Path) -> None:
    """Set up project structure from a configuration file."""
    configure_logging()
    setup_project(config)


@app.command("prepare")
def prepare(
    project_name: str | None = PROJECT_NAME_OPTIONAL,
    output_dir: Path | None = OUTPUT_DIR_OPTIONAL,
    replicas: int | None = REPLICAS_OPTIONAL,
    temperature: float | None = TEMPERATURE_OPTIONAL,
    engine: str | None = ENGINE_OPTIONAL,
    force_field: str | None = FORCE_FIELD_OPTIONAL,
    water_model: str | None = WATER_MODEL_OPTIONAL,
    production_runs: int | None = PRODUCTION_RUNS_OPTIONAL,
    apo_pdb: Path | None = APO_PDB_OPTION,
    holo_pdb: Path | None = HOLO_PDB_OPTION,
    config: Path | None = CONFIG_OPTION,
) -> None:
    """Prepare apo/holo simulation scaffolding from CLI arguments."""

    configure_logging()

    project_config = ConfigLoader().load_project_config(config) if config is not None else None
    selected_project_name = project_name or (project_config.project_name if project_config else None)
    if selected_project_name is None:
        raise typer.BadParameter("Project name is required when --config is not provided.")

    base_config = project_config or ProjectConfig(project_name=selected_project_name)
    merged_config = base_config.model_copy(deep=True)
    merged_config.project_name = selected_project_name

    if output_dir is not None:
        merged_config.output_dir = str(output_dir)
    if replicas is not None:
        merged_config.simulation.replicas = replicas
    if temperature is not None:
        merged_config.simulation.temperature = temperature
    if production_runs is not None:
        merged_config.simulation.production_runs = production_runs
    if engine is not None:
        merged_config.engine.name = engine
    if force_field is not None:
        merged_config.engine.force_field = force_field
    if water_model is not None:
        merged_config.engine.water_model = water_model
    if apo_pdb is not None:
        merged_config.protein.pdb_files["apo"] = str(apo_pdb)
    if holo_pdb is not None:
        merged_config.protein.pdb_files["holo"] = str(holo_pdb)

    root = StructureBuilder(merged_config).build()
    summary = Table(title="prepmd prepare summary")
    summary.add_column("Setting")
    summary.add_column("Value")
    summary.add_row("Project", merged_config.project_name)
    summary.add_row("Engine", merged_config.engine.name)
    summary.add_row("Force field", merged_config.engine.force_field)
    summary.add_row("Water model", merged_config.engine.water_model)
    summary.add_row("Replicas/variant", str(merged_config.simulation.replicas))
    summary.add_row("Output", str(root))
    console.print(summary)


def main() -> None:
    """Run CLI app."""
    app()
