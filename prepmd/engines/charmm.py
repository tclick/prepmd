"""CHARMM engine implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class CharmmEngine(Engine):
    """CHARMM simulation engine."""

    @property
    def name(self) -> str:
        return "charmm"

    @property
    def supported_box_shapes(self) -> set[str]:
        return {"cubic", "orthorhombic"}

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        cutoff, spacing = self.get_cutoff_spacing(config)
        return [
            "* CHARMM input",
            f"* Project: {config.project_name}",
            "BOMLEV -2",
            f"* Water box: {config.water_box.shape}",
            f"* Suggested cutoff={cutoff:.3f} spacing={spacing:.3f}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        geometry = self.get_box_geometry(config)
        x, y, z = geometry.dimensions
        cutoff, spacing = self.get_cutoff_spacing(config)
        return (
            f"* CHARMM prep from {pdb_ref}\n"
            f"* Force field: {config.engine.force_field}, water: {config.engine.water_model}\n"
            f"* Box shape: {geometry.name}\n"
            f"* Crystal dimensions: {x:.3f} {y:.3f} {z:.3f} 90.0 90.0 90.0\n"
            f"* Suggested cutoff {cutoff:.3f} spacing {spacing:.3f}\n"
            "read rtf card name top_all36_prot.rtf\n"
            "read param card name par_all36m_prot.prm\n"
        )
