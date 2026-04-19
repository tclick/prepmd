"""Amber engine plugin implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine, EngineCapabilities

AVOGADRO_PER_A3_FACTOR = 6.02214076e-4


class AmberEngine(Engine):
    """Amber simulation engine."""

    _CAPABILITIES = EngineCapabilities(
        supported_ensembles=frozenset({"NVT", "NPT", "NVE"}),
        supported_box_shapes=frozenset({"cubic", "truncated_octahedron", "orthorhombic"}),
    )

    @property
    def name(self) -> str:
        return "amber"

    @property
    def capabilities(self) -> EngineCapabilities:
        return self._CAPABILITIES

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        cutoff, spacing = self.get_cutoff_spacing(config)
        return [
            "source leaprc.protein.ff19SB",
            f"source leaprc.water.{config.engine.water_model.lower()}",
            f"# Project: {config.project_name}",
            f"# Water box: {config.water_box.shape}",
            f"# Suggested cutoff={cutoff:.3f} spacing={spacing:.3f}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        geometry = self.get_box_geometry(config)
        cutoff, spacing = self.get_cutoff_spacing(config)
        remarks = "\n".join(f"# {line}" for line in geometry.generate_pdb_remarks())
        if geometry.name == "cubic":
            solvation = f"solvatebox mol {config.engine.water_model.upper()}BOX {config.water_box.side_length:.3f}"
        elif geometry.name == "truncated_octahedron":
            solvation = f"solvateoct mol {config.engine.water_model.upper()}BOX {config.water_box.edge_length:.3f}"
        else:
            x, y, z = geometry.dimensions
            max_dim = max(x, y, z)
            solvation = (
                f"solvatebox mol {config.engine.water_model.upper()}BOX {max_dim:.3f}\n"
                f"setBox mol centers {{{x:.3f} {y:.3f} {z:.3f}}}"
            )
        ion_commands = self._build_ion_commands(config, geometry.volume)
        return (
            f"source leaprc.protein.{config.engine.force_field}\n"
            f"source leaprc.water.{config.engine.water_model.lower()}\n"
            f"{remarks}\n"
            f"mol = loadpdb {pdb_ref}\n"
            f"{solvation}\n"
            f"{ion_commands}"
            f"# cutoff {cutoff:.3f} spacing {spacing:.3f}\n"
            "saveamberparm mol system.prmtop system.inpcrd\n"
            "quit\n"
        )

    @staticmethod
    def _build_ion_commands(config: ProjectConfig, volume_a3: float) -> str:
        if not config.water_box.include_ions:
            return ""

        lines: list[str] = []
        cation = config.water_box.cation.value
        anion = config.water_box.anion.value

        if config.water_box.neutralize_protein:
            lines.append(f"addions2 mol {cation} 0 {anion} 0")

        concentration = config.water_box.ion_concentration_molar
        ion_pairs = round(volume_a3 * concentration * AVOGADRO_PER_A3_FACTOR)
        if ion_pairs > 0:
            lines.append(f"addionsrand mol {cation} {ion_pairs} {anion} {ion_pairs}")
        else:
            lines.append(f"# ion concentration {concentration:.3f} M yields <1 ion pair for this box volume")

        return "\n".join(lines) + "\n"
