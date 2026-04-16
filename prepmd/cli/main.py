"""Command line entrypoint."""

from pathlib import Path

import typer

from prepmd.cli.commands.setup import setup_project

LICENSE_TEXT = "GNU GPL-3.0-or-later"

app = typer.Typer(help="prepmd CLI")


@app.command("license")
def show_license() -> None:
    """Display project license."""
    typer.echo(LICENSE_TEXT)


@app.command("setup")
def setup(config: Path) -> None:
    """Set up project structure from a configuration file."""
    setup_project(config)


def main() -> None:
    """Run CLI app."""
    app()
