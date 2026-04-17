"""Command line entrypoint."""

from pathlib import Path
from typing import cast

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TaskProgressColumn, TextColumn
from rich.table import Table

from prepmd.cli.commands.setup import setup_project
from prepmd.cli.run_artifacts import (
    build_manifest,
    plan_preview,
    read_generated_files,
    stable_json,
    write_debug_bundle,
    write_manifest,
)
from prepmd.config.loader import ConfigLoader
from prepmd.config.models import (
    EngineConfig,
    EngineName,
    ProjectConfig,
    ProteinConfig,
    SimulationConfig,
    WaterBoxConfig,
    WaterBoxShape,
)
from prepmd.core.run import PlannedFile, SimulationPlan, apply_plan, build_plan, render_prepare_files
from prepmd.exceptions import PDBMutualExclusivityError, PrepMDError
from prepmd.models.results import RunResult
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
DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    help="Validate and build a plan preview without writing project files.",
)
DEBUG_BUNDLE_OPTION = typer.Option(None, "--debug-bundle", help="Write a debug zip bundle at the provided path.")

app = typer.Typer(help="prepmd CLI")


class RichProgressReporter:
    """Reporter implementation using Rich progress + console logs."""

    def __init__(self, rich_console: Console) -> None:
        self._console = rich_console
        self._progress = Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=rich_console,
            transient=True,
        )
        self._task_id: TaskID | None = None
        self.logs: list[str] = []

    def on_start(self, total_steps: int) -> None:
        self._progress.start()
        self._task_id = self._progress.add_task("Preparing project", total=max(total_steps, 1))

    def on_step(self, current_step: int, total_steps: int, message: str) -> None:
        self.logs.append(f"STEP {current_step}/{total_steps}: {message}")
        if self._task_id is None:
            self.on_start(total_steps)
        if self._task_id is not None:
            self._progress.update(self._task_id, completed=current_step, description=message)

    def on_log(self, message: str) -> None:
        self.logs.append(f"LOG: {message}")
        self._console.print(message)

    def on_error(self, error: BaseException) -> None:
        self.logs.append(f"ERROR: {error}")
        self._console.print(f"[bold red]Error:[/bold red] {error}")
        self._progress.stop()

    def on_finish(self, result: RunResult) -> None:
        _ = result
        self._progress.stop()


def _render_exception_group(exc: ExceptionGroup, title: str = "Errors") -> None:
    console.print(f"[bold red]{title}:[/bold red]")
    for line in _flatten_exception_group(exc):
        console.print(f"- {line}")


def _flatten_exception_group(exc: BaseExceptionGroup[BaseException]) -> list[str]:
    messages: list[str] = []
    for sub_exc in exc.exceptions:
        if isinstance(sub_exc, BaseExceptionGroup):
            messages.extend(_flatten_exception_group(cast(BaseExceptionGroup[BaseException], sub_exc)))
        else:
            messages.append(str(sub_exc))
    return messages


@app.command("license")
def show_license() -> None:
    """Display project license."""
    console.print(f"[bold green]{LICENSE_TEXT}[/bold green]")


@app.command("setup")
def setup(
    config: Path,
    dry_run: bool = DRY_RUN_OPTION,
    debug_bundle: Path | None = DEBUG_BUNDLE_OPTION,
) -> None:
    """Set up project structure from a configuration file."""
    configure_logging()
    try:
        setup_project(config, dry_run=dry_run, debug_bundle=debug_bundle)
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
    dry_run: bool = DRY_RUN_OPTION,
    debug_bundle: Path | None = DEBUG_BUNDLE_OPTION,
) -> None:
    """Prepare apo/holo simulation scaffolding from CLI arguments."""

    configure_logging()

    try:
        project_config = ConfigLoader().load_project_config(config) if config is not None else None
        selected_project_name = project_name or (project_config.project_name if project_config else None)
        if selected_project_name is None:
            raise typer.BadParameter("Project name is required when --config is not provided.")

        if project_config is not None:
            merged_config = project_config.model_copy(deep=True)
            merged_config.project_name = selected_project_name
        else:
            merged_config = ProjectConfig.model_construct(
                project_name=selected_project_name,
                output_dir=".",
                protein=ProteinConfig.model_construct(),
                simulation=SimulationConfig(),
                engine=EngineConfig(),
                water_box=WaterBoxConfig(),
            )

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

        # Guard "neither set" before model_validate so the error is consistent
        # with the pipeline validator message (not a raw pydantic exception).
        _has_variant_local = any(v for v in merged_config.protein.pdb_files.values() if v)
        _has_local = merged_config.protein.pdb_file is not None or _has_variant_local
        _has_remote = merged_config.protein.pdb_id is not None
        if not _has_local and not _has_remote:
            raise PDBMutualExclusivityError(
                "Specify exactly one PDB input method: local file(s), variant-specific files, or PDB ID."
            )

        merged_config = ProjectConfig.model_validate(merged_config.model_dump())
        plan = build_plan(merged_config)
        run_result = None
        logs: list[str] = []
        root = plan.root_dir
        if dry_run:
            generated_files = _collect_generated_files(plan, dry_run=True)
            logs.append("Dry-run mode enabled; skipped apply step.")
            console.print("[bold yellow]Dry-run:[/bold yellow] no project files were written.")
        else:
            reporter = RichProgressReporter(console)
            setup_result = apply_plan(plan, reporter=reporter)
            run_result = setup_result.result
            logs.extend(reporter.logs)
            generated_files = _collect_generated_files(plan, dry_run=False)

        manifest = build_manifest(merged_config, plan, generated_files, dry_run=dry_run)
        preview = plan_preview(plan, generated_files)
        if dry_run:
            console.print_json(stable_json(manifest))
        else:
            manifest_path = root / "manifest.json"
            write_manifest(manifest_path, manifest)
            logs.append(f"Wrote manifest: {manifest_path}")

        if debug_bundle is not None:
            write_debug_bundle(
                debug_bundle,
                config=merged_config,
                manifest=manifest,
                plan_text=preview,
                logs=logs,
                run_result=run_result,
            )
            console.print(f"[green]Debug bundle written:[/green] {debug_bundle}")
    except ExceptionGroup as exc:
        _render_exception_group(exc, "Validation errors")
        raise typer.Exit(code=1) from exc
    except PydanticValidationError as exc:
        console.print("[bold red]Validation errors:[/bold red]")
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            console.print(f"- {location}: {error['msg']}")
        raise typer.Exit(code=1) from exc
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


def _collect_generated_files(plan: SimulationPlan, *, dry_run: bool) -> tuple[PlannedFile, ...]:
    if dry_run:
        predicted_prepare = render_prepare_files(plan, download_remote_pdb=False)
        return tuple(sorted((*plan.files, *predicted_prepare), key=lambda item: str(item.path)))
    return read_generated_files(plan)
