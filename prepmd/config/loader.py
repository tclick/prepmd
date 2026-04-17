"""Main configuration loader with format detection."""

from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from prepmd.config.loaders.toml_loader import TOMLConfigLoader
from prepmd.config.loaders.yaml_loader import YAMLConfigLoader
from prepmd.config.models import ProjectConfig
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.exceptions import ConfigurationError, PDBMutualExclusivityError


class ConfigLoader:
    """Load and parse project configuration files."""

    def __init__(self) -> None:
        self._yaml = YAMLConfigLoader()
        self._toml = TOMLConfigLoader()
        self._pipeline = ValidationPipeline()

    def load_project_config(self, path: str | Path) -> ProjectConfig:
        file_path = Path(path)
        if file_path.suffix.lower() in {".yaml", ".yml"}:
            data = self._yaml.load(file_path)
        elif file_path.suffix.lower() == ".toml":
            data = self._toml.load(file_path)
        else:
            raise ConfigurationError(f"Unsupported config format: {file_path.suffix}")

        try:
            config = ProjectConfig.model_validate(data)
        except PydanticValidationError as exc:
            error_messages = "\n".join(str(error.get("msg", error)) for error in exc.errors())
            if "PDB input method" in error_messages or "local PDB file or a PDB ID" in error_messages:
                raise PDBMutualExclusivityError(error_messages) from exc
            raise ConfigurationError(error_messages) from exc
        self._pipeline.validate(config)
        return config
