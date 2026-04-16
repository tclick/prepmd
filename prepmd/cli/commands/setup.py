"""Setup command implementation."""

from pathlib import Path

import typer

from prepmd.config.loader import ConfigLoader
from prepmd.structure_builder.builder import StructureBuilder


def setup_project(config_path: Path) -> None:
    """Load config and scaffold project directories."""
    config = ConfigLoader().load_project_config(config_path)
    root = StructureBuilder(config).build()
    typer.echo(f"Project created at {root}")
