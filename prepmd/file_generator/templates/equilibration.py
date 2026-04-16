"""Equilibration template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.comments import build_header_comment


def render_equilibration(config: ProjectConfig) -> str:
    return (
        build_header_comment(config, "equilibration")
        + f"ensemble={config.simulation.ensemble}\n"
        + "nstlim=250000\n"
    )
