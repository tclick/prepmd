"""OpenMM engine plugin implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class OpenmmEngine(Engine):
    """OpenMM simulation engine."""

    @property
    def name(self) -> str:
        return "openmm"

    @property
    def supported_box_shapes(self) -> set[str]:
        return {"cubic", "truncated_octahedron", "orthorhombic"}

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        cutoff, spacing = self.get_cutoff_spacing(config)
        return [
            "from openmm import LangevinIntegrator",
            f"temperature = {config.simulation.temperature:.1f}",
            f"force_field = '{config.engine.force_field}'",
            f"water_box_shape = '{config.water_box.shape}'",
            f"cutoff = {cutoff:.3f}",
            f"spacing = {spacing:.3f}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        geometry = self.get_box_geometry(config)
        x, y, z = geometry.dimensions
        cutoff, spacing = self.get_cutoff_spacing(config)
        return (
            "from openmm.app import PDBFile, ForceField, Modeller\n"
            f"pdb = PDBFile('{pdb_ref}')\n"
            f"ff = ForceField('{config.engine.force_field}.xml', '{config.engine.water_model}.xml')\n"
            "modeller = Modeller(pdb.topology, pdb.positions)\n"
            f"box_vectors = ({x:.3f}, {y:.3f}, {z:.3f})\n"
            f"modeller.addSolvent(ff, boxSize=box_vectors, model='{config.engine.water_model.lower()}')\n"
            f"# box shape: {config.water_box.shape}\n"
            f"# suggested cutoff {cutoff:.3f} spacing {spacing:.3f}\n"
        )

