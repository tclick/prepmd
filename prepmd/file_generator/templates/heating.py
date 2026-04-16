"""Heating template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.comments import build_header_comment


def render_heating(config: ProjectConfig) -> str:
    return (
        build_header_comment(config, "heating")
        + f"temp0={config.simulation.temperature}\n"
        + "ntt=3\n"
    )
