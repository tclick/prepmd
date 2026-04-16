"""OpenMM engine implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class OpenmmEngine(Engine):
    """OpenMM simulation engine."""

    @property
    def name(self) -> str:
        return "openmm"

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        return [
            "from openmm import LangevinIntegrator",
            f"temperature = {config.simulation.temperature:.1f}",
            f"force_field = '{config.engine.force_field}'",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        return (
            "from openmm.app import PDBFile, ForceField, Modeller\n"
            f"pdb = PDBFile('{pdb_ref}')\n"
            f"ff = ForceField('{config.engine.force_field}.xml', '{config.engine.water_model}.xml')\n"
            "modeller = Modeller(pdb.topology, pdb.positions)\n"
            "modeller.addSolvent(ff)\n"
        )
