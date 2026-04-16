"""Heating template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.base import FileGenerator
from prepmd.file_generator.comments import build_header_comment


class HeatingFileGenerator(FileGenerator):
    """Render an NVT heating input file."""

    def render(self, config: ProjectConfig) -> str:
        return (
            build_header_comment(config, "heating")
            + f"temp0={config.simulation.temperature}\n"
            + "ntt=3\n"
        )


def render_heating(config: ProjectConfig) -> str:
    return HeatingFileGenerator().render(config)
