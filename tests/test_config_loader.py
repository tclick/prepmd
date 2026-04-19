from pathlib import Path

import pytest

from prepmd.config.loader import ConfigLoader
from prepmd.exceptions import PDBMutualExclusivityError


def test_load_yaml_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "project_name: demo\nprotein:\n  variants: [wt]\n  pdb_file: /tmp/input.pdb\nsimulation:\n  replicas: 2\n",
        encoding="utf-8",
    )

    config = ConfigLoader().load_project_config(config_path)

    assert config.project_name == "demo"
    assert config.protein.variants == ["wt"]
    assert config.simulation.replicas == 2


def test_load_toml_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        'project_name = "demo"\n[simulation]\nreplicas = 3\n[protein]\npdb_file = "/tmp/input.pdb"\n',
        encoding="utf-8",
    )

    config = ConfigLoader().load_project_config(config_path)

    assert config.project_name == "demo"
    assert config.simulation.replicas == 3


def test_load_config_with_truncated_octahedron_water_box(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        (
            "project_name: demo\n"
            "protein:\n"
            "  pdb_file: /tmp/input.pdb\n"
            "water_box:\n"
            "  shape: truncated_octahedron\n"
            "  edge_length: 10.0\n"
        ),
        encoding="utf-8",
    )

    config = ConfigLoader().load_project_config(config_path)
    assert config.water_box.shape == "truncated_octahedron"
    assert config.water_box.edge_length == 10.0


def test_load_config_with_ionized_water_box(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        (
            "project_name: demo\n"
            "protein:\n"
            "  pdb_file: /tmp/input.pdb\n"
            "water_box:\n"
            "  shape: cubic\n"
            "  side_length: 60.0\n"
            "  include_ions: true\n"
            "  neutralize_protein: true\n"
            "  ion_concentration_molar: 0.2\n"
            "  cation: K+\n"
            "  anion: Cl-\n"
        ),
        encoding="utf-8",
    )

    config = ConfigLoader().load_project_config(config_path)
    assert config.water_box.include_ions
    assert config.water_box.neutralize_protein
    assert config.water_box.ion_concentration_molar == 0.2
    assert config.water_box.cation == "K+"
    assert config.water_box.anion == "Cl-"


def test_load_config_rejects_both_pdb_id_and_pdb_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "project_name: demo\nprotein:\n  pdb_file: /tmp/input.pdb\n  pdb_id: 1abc\n",
        encoding="utf-8",
    )

    with pytest.raises(PDBMutualExclusivityError):
        ConfigLoader().load_project_config(config_path)


def test_load_config_rejects_both_variant_pdb_id_and_pdb_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "project_name: demo\nprotein:\n  pdb_file: /tmp/input.pdb\n  pdb_ids:\n    apo: 1abc\n",
        encoding="utf-8",
    )

    with pytest.raises(PDBMutualExclusivityError):
        ConfigLoader().load_project_config(config_path)


def test_load_config_accepts_variant_pdb_ids(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "project_name: demo\nprotein:\n  variants: [apo, holo]\n  pdb_ids:\n    apo: 1abc\n    holo: 2xyz\n",
        encoding="utf-8",
    )

    config = ConfigLoader().load_project_config(config_path)

    assert config.protein.pdb_ids == {"apo": "1abc", "holo": "2xyz"}


def test_load_config_requires_pdb_input_method(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project_name: demo\n", encoding="utf-8")

    with pytest.raises(PDBMutualExclusivityError):
        ConfigLoader().load_project_config(config_path)
