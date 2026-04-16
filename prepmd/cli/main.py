"""Command line entrypoint."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from prepmd.cli.commands.setup import setup_project
from prepmd.config.models import EngineConfig, ProjectConfig, ProteinConfig, SimulationConfig
from prepmd.structure_builder.builder import StructureBuilder
from prepmd.utils.logging import configure_logging

LICENSE_TEXT = "GNU GPL-3.0-or-later"
SUPPORTED_ENGINES = ["amber", "namd", "gromacs", "charmm", "openmm"]
console = Console()
PROJECT_NAME_OPTION = typer.Option(..., help="Project name.")
OUTPUT_DIR_OPTION = typer.Option(Path("."), help="Output directory.")
REPLICAS_OPTION = typer.Option(1, min=1, help="Replicas per variant.")
TEMPERATURE_OPTION = typer.Option(300.0, min=1.0, help="Target temperature in K.")
ENGINE_OPTION = typer.Option("amber", help=f"Engine name ({', '.join(SUPPORTED_ENGINES)}).")
FORCE_FIELD_OPTION = typer.Option("ff19sb", help="Force field name.")
WATER_MODEL_OPTION = typer.Option("OPC3", help="Water model name.")
PRODUCTION_RUNS_OPTION = typer.Option(3, min=1, help="Number of 100-ns production segments.")
APO_PDB_OPTION = typer.Option(None, help="Apo input PDB file.")
HOLO_PDB_OPTION = typer.Option(None, help="Holo input PDB file.")

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
    project_name: str = PROJECT_NAME_OPTION,
    output_dir: Path = OUTPUT_DIR_OPTION,
    replicas: int = REPLICAS_OPTION,
    temperature: float = TEMPERATURE_OPTION,
    engine: str = ENGINE_OPTION,
    force_field: str = FORCE_FIELD_OPTION,
    water_model: str = WATER_MODEL_OPTION,
    production_runs: int = PRODUCTION_RUNS_OPTION,
    apo_pdb: Path | None = APO_PDB_OPTION,
    holo_pdb: Path | None = HOLO_PDB_OPTION,
) -> None:
    """Prepare apo/holo simulation scaffolding from CLI arguments."""

    configure_logging()
    config = ProjectConfig(
        project_name=project_name,
        output_dir=str(output_dir),
        protein=ProteinConfig(
            variants=["apo", "holo"],
            pdb_files={
                "apo": str(apo_pdb) if apo_pdb is not None else None,
                "holo": str(holo_pdb) if holo_pdb is not None else None,
            },
        ),
        simulation=SimulationConfig(replicas=replicas, temperature=temperature, production_runs=production_runs),
        engine=EngineConfig(name=engine, force_field=force_field, water_model=water_model),
    )
    root = StructureBuilder(config).build()
    summary = Table(title="prepmd prepare summary")
    summary.add_column("Setting")
    summary.add_column("Value")
    summary.add_row("Project", project_name)
    summary.add_row("Engine", engine.lower())
    summary.add_row("Force field", force_field)
    summary.add_row("Water model", water_model)
    summary.add_row("Replicas/variant", str(replicas))
    summary.add_row("Output", str(root))
    console.print(summary)


def main() -> None:
    """Run CLI app."""
    app()
