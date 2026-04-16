"""Equilibration template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.base import FileGenerator
from prepmd.file_generator.comments import build_header_comment


class EquilibrationFileGenerator(FileGenerator):
    """Render an NPT equilibration input file."""

    def render(self, config: ProjectConfig) -> str:
        return (
            build_header_comment(config, "equilibration")
            + f"ensemble={config.simulation.ensemble}\n"
            + "nstlim=250000\n"
        )


def render_equilibration(config: ProjectConfig) -> str:
    return EquilibrationFileGenerator().render(config)
