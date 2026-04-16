"""tleap command file builder."""

from prepmd.config.models import ProjectConfig


def build_tleap_commands(config: ProjectConfig) -> str:
    """Generate a minimal tleap command file from project config."""
    return (
        "source leaprc.protein.ff14SB\n"
        f"# project: {config.project_name}\n"
        "quit\n"
    )
