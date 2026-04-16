"""Minimization template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.base import FileGenerator
from prepmd.file_generator.comments import build_header_comment


class MinimizationFileGenerator(FileGenerator):
    """Render a minimization input file."""

    def render(self, config: ProjectConfig) -> str:
        return build_header_comment(config, "minimization") + "imin=1\nmaxcyc=5000\n"


def render_minimization(config: ProjectConfig) -> str:
    return MinimizationFileGenerator().render(config)
