"""Amber engine implementation."""

from prepmd.config.models import ProjectConfig
from prepmd.engines.base import Engine


class AmberEngine(Engine):
    """Amber simulation engine."""

    @property
    def name(self) -> str:
        return "amber"

    def generate_inputs(self, config: ProjectConfig) -> list[str]:
        return [
            "source leaprc.protein.ff19SB",
            f"source leaprc.water.{config.engine.water_model.lower()}",
            f"# Project: {config.project_name}",
        ]

    def prepare_from_pdb(self, pdb_file: str | None, config: ProjectConfig) -> str:
        pdb_ref = pdb_file or "input.pdb"
        return (
            f"source leaprc.protein.{config.engine.force_field}\n"
            f"source leaprc.water.{config.engine.water_model.lower()}\n"
            f"mol = loadpdb {pdb_ref}\n"
            "solvatebox mol OPC3BOX 10.0\n"
            "saveamberparm mol system.prmtop system.inpcrd\n"
            "quit\n"
        )
