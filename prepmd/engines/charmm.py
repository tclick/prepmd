"""CHARMM engine implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class CharmmEngine(Engine):
    """CHARMM simulation engine."""

    @property
    def name(self) -> str:
        return "charmm"

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        return [
            "* CHARMM input",
            f"* Project: {config.project_name}",
            "BOMLEV -2",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        return (
            f"* CHARMM prep from {pdb_ref}\n"
            f"* Force field: {config.engine.force_field}, water: {config.engine.water_model}\n"
            "read rtf card name top_all36_prot.rtf\n"
            "read param card name par_all36m_prot.prm\n"
        )
