"""Setup command implementation."""

from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.table import Table

from prepmd.cli.run_artifacts import (
    build_manifest,
    plan_preview,
    read_generated_files,
    write_debug_bundle,
    write_manifest,
)
from prepmd.config.loader import ConfigLoader
from prepmd.core.reporting import NullReporter
from prepmd.core.run import apply_plan, build_plan, render_prepare_files
from prepmd.models.results import RunResult

console = Console()


def setup_project(config_path: Path, *, dry_run: bool = False, debug_bundle: Path | None = None) -> None:
    """Load config and scaffold project directories."""
    config = ConfigLoader().load_project_config(config_path)
    plan = build_plan(config)
    root = plan.root_dir
    logs: list[str] = []
    run_result: RunResult | None = None
    if dry_run:
        predicted_prepare = render_prepare_files(plan, download_remote_pdb=False)
        generated_files = tuple(sorted((*plan.files, *predicted_prepare), key=lambda item: str(item.path)))
        logs.append("Dry-run mode enabled; skipped apply step.")
    else:
        result = apply_plan(plan, reporter=NullReporter())
        run_result = result.result
        generated_files = read_generated_files(plan)
        logger.info(f"Project created at {root}")

    manifest = build_manifest(config, plan, generated_files, dry_run=dry_run)
    if dry_run:
        logger.info(f"Dry-run validated plan for {root}")
    else:
        manifest_path = root / "manifest.json"
        write_manifest(manifest_path, manifest)
        logs.append(f"Wrote manifest: {manifest_path}")

    if debug_bundle is not None:
        write_debug_bundle(
            debug_bundle,
            config=config,
            manifest=manifest,
            plan_text=plan_preview(plan, generated_files),
            logs=logs,
            run_result=run_result,
        )
        logger.info(f"Debug bundle written to {debug_bundle}")

    table = Table(title="prepmd setup")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Project", config.project_name)
    table.add_row("Engine", config.engine.name)
    table.add_row("Path", str(root))
    table.add_row("Mode", "dry-run" if dry_run else "apply")
    console.print(table)
