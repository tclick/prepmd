"""Gromacs engine plugin implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine, EngineCapabilities


class GromacsEngine(Engine):
    """Gromacs simulation engine."""

    _CAPABILITIES = EngineCapabilities(
        supported_ensembles=frozenset({"NVT", "NPT", "NVE"}),
        supported_box_shapes=frozenset({"cubic", "truncated_octahedron", "orthorhombic"}),
    )

    @property
    def name(self) -> str:
        return "gromacs"

    @property
    def capabilities(self) -> EngineCapabilities:
        return self._CAPABILITIES

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        cutoff, spacing = self.get_cutoff_spacing(config)
        return [
            "integrator = md",
            f"ref_t = {config.simulation.temperature:.1f}",
            f"; force field: {config.engine.force_field}",
            f"; water box: {config.water_box.shape}",
            f"; suggested cutoff={cutoff:.3f} spacing={spacing:.3f}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        geometry = self.get_box_geometry(config)
        x, y, z = geometry.dimensions
        cutoff, spacing = self.get_cutoff_spacing(config)
        shape_map = {
            "cubic": "cubic",
            "truncated_octahedron": "octahedron",
            "orthorhombic": "triclinic",
        }
        editconf_args = f"-box {x:.3f} {y:.3f} {z:.3f} -bt {shape_map[geometry.name]}"
        return (
            f"gmx pdb2gmx -f {pdb_ref} -o processed.gro -ff {config.engine.force_field} "
            f"-water {config.engine.water_model.lower()}\n"
            f"gmx editconf -f processed.gro -o boxed.gro -c {editconf_args}\n"
            "gmx solvate -cp boxed.gro -cs spc216.gro -o solvated.gro -p topol.top\n"
            f"# cutoff {cutoff:.3f} spacing {spacing:.3f}\n"
        )
