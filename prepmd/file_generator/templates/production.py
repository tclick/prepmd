"""Production template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.comments import build_header_comment


def render_production(config: ProjectConfig) -> str:
    return build_header_comment(config, "production") + "nstlim=500000\n"
