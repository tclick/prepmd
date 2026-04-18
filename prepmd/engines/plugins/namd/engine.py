"""NAMD engine plugin implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class NamdEngine(Engine):
    """NAMD simulation engine."""

    @property
    def name(self) -> str:
        return "namd"

    @property
    def supported_box_shapes(self) -> set[str]:
        return {"cubic", "orthorhombic"}

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        cutoff, spacing = self.get_cutoff_spacing(config)
        return [
            "structure system.psf",
            "coordinates system.pdb",
            f"# Temperature: {config.simulation.temperature:.1f}",
            f"# Water box: {config.water_box.shape}",
            f"# Suggested cutoff={cutoff:.3f} spacing={spacing:.3f}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        geometry = self.get_box_geometry(config)
        x, y, z = geometry.dimensions
        cutoff, spacing = self.get_cutoff_spacing(config)
        return (
            f"# NAMD prep from {pdb_ref}\n"
            f"# Force field: {config.engine.force_field}\n"
            f"# Water model: {config.engine.water_model}\n"
            f"# Box shape: {geometry.name}\n"
            f"# Cell basis vectors: ({x:.3f}, 0, 0) (0, {y:.3f}, 0) (0, 0, {z:.3f})\n"
            f"# Suggested cutoff {cutoff:.3f} spacing {spacing:.3f}\n"
            "autopsf -top top_all36_prot.rtf -top par_all36m_prot.prm system.pdb\n"
        )

