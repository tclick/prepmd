"""Setup command implementation."""

from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.table import Table

from prepmd.config.loader import ConfigLoader
from prepmd.structure_builder.builder import StructureBuilder

console = Console()


def setup_project(config_path: Path) -> None:
    """Load config and scaffold project directories."""
    config = ConfigLoader().load_project_config(config_path)
    root = StructureBuilder(config).build()
    logger.info(f"Project created at {root}")
    table = Table(title="prepmd setup")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Project", config.project_name)
    table.add_row("Engine", config.engine.name)
    table.add_row("Path", str(root))
    console.print(table)
