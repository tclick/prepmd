"""Template configuration generation for `prepmd init`."""

import tomllib
from enum import StrEnum
from pathlib import Path

import yaml

from prepmd.config.models import ProjectConfig


class InitFormat(StrEnum):
    """Supported `prepmd init` output formats."""

    YAML = "yaml"
    TOML = "toml"


_YAML_TEMPLATE = """# prepmd configuration template
# Example project-level settings.
project_name: demo
output_dir: .

# Example PDB input via protein.pdb_id (remote download from RCSB).
protein:
  pdb_id: "1ABC"

# Typical simulation settings.
simulation:
  replicas: 1
  temperature: 300.0
  ensemble: NVT
  production_runs: 3
  production_run_length_ns: 100

# Typical engine settings with OPC water model.
engine:
  name: amber
  force_field: ff19sb
  water_model: OPC

# Example orthorhombic water box dimensions in Å.
water_box:
  shape: orthorhombic
  dimensions: [60.0, 60.0, 80.0]
  include_ions: true
  neutralize_protein: true
  ion_concentration_molar: 0.15
  cation: Na+
  anion: Cl-
"""

_TOML_TEMPLATE = """# prepmd configuration template
# Example project-level settings.
project_name = "demo"
output_dir = "."

# Example PDB input via protein.pdb_id (remote download from RCSB).
[protein]
pdb_id = "1ABC"

# Typical simulation settings.
[simulation]
replicas = 1
temperature = 300.0
ensemble = "NVT"
production_runs = 3
production_run_length_ns = 100

# Typical engine settings with OPC water model.
[engine]
name = "amber"
force_field = "ff19sb"
water_model = "OPC"

# Example orthorhombic water box dimensions in Å.
[water_box]
shape = "orthorhombic"
dimensions = [60.0, 60.0, 80.0]
include_ions = true
neutralize_protein = true
ion_concentration_molar = 0.15
cation = "Na+"
anion = "Cl-"
"""


def default_output_path(config_format: InitFormat) -> Path:
    """Return default output path for a given format."""
    return Path("prepmd.yaml" if config_format == InitFormat.YAML else "prepmd.toml")


def render_template(config_format: InitFormat) -> str:
    """Render a template string in the requested format."""
    return _YAML_TEMPLATE if config_format == InitFormat.YAML else _TOML_TEMPLATE


def validate_template(config_text: str, config_format: InitFormat) -> None:
    """Validate generated template against ProjectConfig."""
    loaded = yaml.safe_load(config_text) if config_format == InitFormat.YAML else tomllib.loads(config_text)
    ProjectConfig.model_validate(loaded)
