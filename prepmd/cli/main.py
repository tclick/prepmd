"""Command line entrypoint."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from prepmd.cli.commands.setup import setup_project
from prepmd.config.loader import ConfigLoader
from prepmd.config.models import EngineName, ProjectConfig, WaterBoxShape
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.exceptions import PDBMutualExclusivityError, PrepMDError
from prepmd.structure_builder.builder import StructureBuilder
from prepmd.utils.logging import configure_logging

LICENSE_TEXT = "GNU GPL-3.0-or-later"
SUPPORTED_ENGINES = [e.value for e in EngineName]
SUPPORTED_BOX_SHAPES = [s.value for s in WaterBoxShape]
console = Console()
PROJECT_NAME_OPTIONAL = typer.Option(None, help="Project name.")
OUTPUT_DIR_OPTIONAL = typer.Option(None, help="Output directory.")
REPLICAS_OPTIONAL = typer.Option(None, min=1, help="Replicas per variant.")
TEMPERATURE_OPTIONAL = typer.Option(None, min=1.0, help="Target temperature in K.")
ENGINE_OPTIONAL = typer.Option(None, help=f"Engine name ({', '.join(SUPPORTED_ENGINES)}).")
FORCE_FIELD_OPTIONAL = typer.Option(None, help="Force field name.")
WATER_MODEL_OPTIONAL = typer.Option(None, help="Water model name.")
PRODUCTION_RUNS_OPTIONAL = typer.Option(None, min=1, help="Number of 100-ns production segments.")
BOX_SHAPE_OPTION = typer.Option(None, help=f"Water box shape ({', '.join(SUPPORTED_BOX_SHAPES)}).")
BOX_SIDE_LENGTH_OPTION = typer.Option(None, min=0.1, help="Water box side length in Å (cubic).")
BOX_EDGE_LENGTH_OPTION = typer.Option(None, min=0.1, help="Water box edge length in Å (truncated octahedron).")
BOX_DIMENSIONS_OPTION = typer.Option(None, help="Water box dimensions X Y Z in Å (orthorhombic).")
AUTO_BOX_PADDING_OPTION = typer.Option(None, min=0.1, help="Automatic box padding in Å (default 10.0).")
PDB_FILE_OPTION = typer.Option(None, help="Input PDB file path.")
PDB_ID_OPTION = typer.Option(None, help="RCSB PDB ID to download (4 alphanumeric chars).")
PDB_CACHE_DIR_OPTION = typer.Option(None, help="Cache directory for downloaded PDB files.")
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
    try:
        setup_project(config)
    except PrepMDError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


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
    box_shape: str | None = BOX_SHAPE_OPTION,
    box_side_length: float | None = BOX_SIDE_LENGTH_OPTION,
    box_edge_length: float | None = BOX_EDGE_LENGTH_OPTION,
    box_dimensions: tuple[float, float, float] | None = BOX_DIMENSIONS_OPTION,
    auto_box_padding: float | None = AUTO_BOX_PADDING_OPTION,
    pdb_file: Path | None = PDB_FILE_OPTION,
    pdb_id: str | None = PDB_ID_OPTION,
    pdb_cache_dir: Path | None = PDB_CACHE_DIR_OPTION,
    apo_pdb: Path | None = APO_PDB_OPTION,
    holo_pdb: Path | None = HOLO_PDB_OPTION,
    config: Path | None = CONFIG_OPTION,
) -> None:
    """Prepare apo/holo simulation scaffolding from CLI arguments."""

    configure_logging()

    try:
        project_config = ConfigLoader().load_project_config(config) if config is not None else None
        selected_project_name = project_name or (project_config.project_name if project_config else None)
        if selected_project_name is None:
            raise typer.BadParameter("Project name is required when --config is not provided.")

        base_config = project_config or ProjectConfig(project_name=selected_project_name)
        merged_config = base_config.model_copy(deep=True)
        merged_config.project_name = selected_project_name

        if pdb_id is not None and (pdb_file is not None or apo_pdb is not None or holo_pdb is not None):
            raise PDBMutualExclusivityError("Specify either a local PDB file or a PDB ID, not both.")

        if output_dir is not None:
            merged_config.output_dir = str(output_dir)
        if replicas is not None:
            merged_config.simulation.replicas = replicas
        if temperature is not None:
            merged_config.simulation.temperature = temperature
        if production_runs is not None:
            merged_config.simulation.production_runs = production_runs
        if box_shape is not None:
            merged_config.water_box.shape = WaterBoxShape(box_shape.lower())
        if auto_box_padding is not None:
            merged_config.water_box.auto_box_padding = auto_box_padding
        if box_side_length is not None:
            merged_config.water_box.shape = WaterBoxShape.CUBIC
            merged_config.water_box.side_length = box_side_length
            merged_config.water_box.edge_length = None
            merged_config.water_box.dimensions = None
        if box_edge_length is not None:
            merged_config.water_box.shape = WaterBoxShape.TRUNCATED_OCTAHEDRON
            merged_config.water_box.edge_length = box_edge_length
            merged_config.water_box.side_length = None
            merged_config.water_box.dimensions = None
        if box_dimensions is not None:
            merged_config.water_box.shape = WaterBoxShape.ORTHORHOMBIC
            merged_config.water_box.dimensions = box_dimensions
            merged_config.water_box.side_length = None
            merged_config.water_box.edge_length = None
        if engine is not None:
            merged_config.engine.name = EngineName(engine.lower())
        if force_field is not None:
            merged_config.engine.force_field = force_field
        if water_model is not None:
            merged_config.engine.water_model = water_model
        if pdb_file is not None:
            merged_config.protein.pdb_file = str(pdb_file)
            merged_config.protein.pdb_id = None
            merged_config.protein.pdb_files = {}
        if pdb_id is not None:
            merged_config.protein.pdb_id = pdb_id
            merged_config.protein.pdb_file = None
            merged_config.protein.pdb_files = {}
        if pdb_cache_dir is not None:
            merged_config.protein.pdb_cache_dir = str(pdb_cache_dir)
        if apo_pdb is not None:
            merged_config.protein.pdb_files["apo"] = str(apo_pdb)
            merged_config.protein.pdb_id = None
        if holo_pdb is not None:
            merged_config.protein.pdb_files["holo"] = str(holo_pdb)
            merged_config.protein.pdb_id = None

        merged_config = ProjectConfig.model_validate(merged_config.model_dump())
        ValidationPipeline().validate(merged_config)
        root = StructureBuilder(merged_config).build()
    except PrepMDError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    summary = Table(title="prepmd prepare summary")
    summary.add_column("Setting")
    summary.add_column("Value")
    summary.add_row("Project", merged_config.project_name)
    summary.add_row("Engine", merged_config.engine.name)
    summary.add_row("Force field", merged_config.engine.force_field)
    summary.add_row("Water model", merged_config.engine.water_model)
    summary.add_row("Water box shape", merged_config.water_box.shape)
    summary.add_row("Replicas/variant", str(merged_config.simulation.replicas))
    summary.add_row("Output", str(root))
    console.print(summary)


def main() -> None:
    """Run CLI app."""
    app()
