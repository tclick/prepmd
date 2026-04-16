"""Production template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.base import FileGenerator
from prepmd.file_generator.comments import build_header_comment


class ProductionFileGenerator(FileGenerator):
    """Render a production MD input file."""

    def render(self, config: ProjectConfig) -> str:
        return build_header_comment(config, "production") + "nstlim=500000\n"


def render_production(config: ProjectConfig) -> str:
    return ProductionFileGenerator().render(config)
