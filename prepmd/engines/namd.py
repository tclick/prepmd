"""NAMD engine implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class NamdEngine(Engine):
    """NAMD simulation engine."""

    @property
    def name(self) -> str:
        return "namd"

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        return [
            "structure system.psf",
            "coordinates system.pdb",
            f"# Temperature: {config.simulation.temperature:.1f}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        return (
            f"# NAMD prep from {pdb_ref}\n"
            f"# Force field: {config.engine.force_field}\n"
            f"# Water model: {config.engine.water_model}\n"
            "autopsf -top top_all36_prot.rtf -top par_all36m_prot.prm system.pdb\n"
        )
