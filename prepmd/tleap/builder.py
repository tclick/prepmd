"""tleap command file builder."""

from prepmd.config.models import ProjectConfig


def build_tleap_commands(config: ProjectConfig) -> str:
    """Generate a minimal tleap command file from project config."""
    return f"source leaprc.protein.ff14SB\n# project: {config.project_name}\nquit\n"
