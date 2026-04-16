"""Main configuration loader with format detection."""

from pathlib import Path

from prepmd.config.loaders.toml_loader import TOMLConfigLoader
from prepmd.config.loaders.yaml_loader import YAMLConfigLoader
from prepmd.config.models import ProjectConfig
from prepmd.exceptions import ConfigurationError


class ConfigLoader:
    """Load and parse project configuration files."""

    def __init__(self) -> None:
        self._yaml = YAMLConfigLoader()
        self._toml = TOMLConfigLoader()

    def load_project_config(self, path: str | Path) -> ProjectConfig:
        file_path = Path(path)
        if file_path.suffix.lower() in {".yaml", ".yml"}:
            data = self._yaml.load(file_path)
        elif file_path.suffix.lower() == ".toml":
            data = self._toml.load(file_path)
        else:
            raise ConfigurationError(f"Unsupported config format: {file_path.suffix}")

        return ProjectConfig.model_validate(data)
