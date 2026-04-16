from pathlib import Path

from prepmd.config.loader import ConfigLoader


def test_load_yaml_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "project_name: demo\nprotein:\n  variants: [wt]\nsimulation:\n  replicas: 2\n",
        encoding="utf-8",
    )

    config = ConfigLoader().load_project_config(config_path)

    assert config.project_name == "demo"
    assert config.protein.variants == ["wt"]
    assert config.simulation.replicas == 2


def test_load_toml_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('project_name = "demo"\n[simulation]\nreplicas = 3\n', encoding="utf-8")

    config = ConfigLoader().load_project_config(config_path)

    assert config.project_name == "demo"
    assert config.simulation.replicas == 3
