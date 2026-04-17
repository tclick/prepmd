"""Setup command implementation."""

from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.table import Table

from prepmd.config.loader import ConfigLoader
from prepmd.core.reporting import NullReporter
from prepmd.core.run import run_setup

console = Console()


def setup_project(config_path: Path) -> None:
    """Load config and scaffold project directories."""
    config = ConfigLoader().load_project_config(config_path)
    result = run_setup(config, reporter=NullReporter())
    root = result.root_dir
    logger.info(f"Project created at {root}")
    table = Table(title="prepmd setup")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Project", config.project_name)
    table.add_row("Engine", config.engine.name)
    table.add_row("Path", str(root))
    console.print(table)
