"""Comment helpers for generated files."""

from prepmd.config.models import ProjectConfig


def build_header_comment(config: ProjectConfig, phase: str) -> str:
    """Build standard comment header for generated files."""
    return f"# prepmd generated file\n# Project: {config.project_name}\n# Phase: {phase}\n"
