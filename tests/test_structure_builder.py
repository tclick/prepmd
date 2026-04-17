from pathlib import Path

from prepmd.config.models import ProjectConfig, ProteinConfig, SimulationConfig
from prepmd.structure_builder.builder import StructureBuilder


def test_structure_builder_creates_expected_directories(tmp_path: Path) -> None:
    config = ProjectConfig(
        project_name="proj",
        output_dir=str(tmp_path),
        protein=ProteinConfig(variants=["wt"], pdb_file="/tmp/input.pdb"),
        simulation=SimulationConfig(replicas=1),
    )

    root = StructureBuilder(config).build()

    assert root == tmp_path / "proj"
    assert (root / "01_input" / "structures").exists()
    assert (root / "05_simulations" / "wt" / "replica_001" / "04_production").exists()
    assert (root / "05_simulations" / "wt" / "replica_001" / "README.md").exists()
    assert (root / "05_simulations" / "wt" / "replica_001" / "PROTOCOL.md").exists()
    assert (root / "05_simulations" / "wt" / "replica_001" / "04_production" / "run_001").exists()
