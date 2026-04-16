from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from hypothesis import given
from hypothesis import strategies as st

from prepmd.config.loader import ConfigLoader


@given(
    project_name=st.from_regex(r"[a-z][a-z0-9_-]{2,12}", fullmatch=True),
    replicas=st.integers(min_value=1, max_value=5),
    temperature=st.floats(min_value=200.0, max_value=400.0, allow_infinity=False, allow_nan=False),
    engine=st.sampled_from(["amber", "gromacs", "namd", "charmm", "openmm"]),
)
def test_yaml_and_toml_support_same_parameter_set(
    project_name: str,
    replicas: int,
    temperature: float,
    engine: str,
) -> None:
    with TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        config_data = {
            "project_name": project_name,
            "output_dir": str(tmp_path),
            "simulation": {"replicas": replicas, "temperature": temperature},
            "engine": {"name": engine, "force_field": "ff19sb", "water_model": "OPC3"},
        }
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

        toml_path = tmp_path / "config.toml"
        toml_path.write_text(
            (
                f'project_name = "{project_name}"\n'
                f'output_dir = "{tmp_path}"\n'
                "[simulation]\n"
                f"replicas = {replicas}\n"
                f"temperature = {temperature}\n"
                "[engine]\n"
                f'name = "{engine}"\n'
                'force_field = "ff19sb"\n'
                'water_model = "OPC3"\n'
            ),
            encoding="utf-8",
        )

        loader = ConfigLoader()
        yaml_config = loader.load_project_config(yaml_path)
        toml_config = loader.load_project_config(toml_path)

        assert yaml_config.model_dump() == toml_config.model_dump()
