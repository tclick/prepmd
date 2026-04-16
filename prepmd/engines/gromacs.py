"""Gromacs engine implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class GromacsEngine(Engine):
    """Gromacs simulation engine."""

    @property
    def name(self) -> str:
        return "gromacs"

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        return [
            "integrator = md",
            f"ref_t = {config.simulation.temperature:.1f}",
            f"; force field: {config.engine.force_field}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        return (
            f"gmx pdb2gmx -f {pdb_ref} -o processed.gro -ff {config.engine.force_field} "
            f"-water {config.engine.water_model.lower()}\n"
            "gmx editconf -f processed.gro -o boxed.gro -c -d 1.0 -bt cubic\n"
            "gmx solvate -cp boxed.gro -cs spc216.gro -o solvated.gro -p topol.top\n"
        )
