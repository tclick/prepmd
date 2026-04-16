"""Minimization template rendering."""

from prepmd.config.models import ProjectConfig
from prepmd.file_generator.comments import build_header_comment


def render_minimization(config: ProjectConfig) -> str:
    return build_header_comment(config, "minimization") + "imin=1\nmaxcyc=5000\n"
