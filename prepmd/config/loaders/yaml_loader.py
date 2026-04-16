"""YAML configuration loader."""

from pathlib import Path
from typing import Any, cast

import yaml

from prepmd.config.loaders.base import BaseConfigLoader
from prepmd.exceptions import ConfigurationError


class YAMLConfigLoader(BaseConfigLoader):
    """Load YAML files into dictionaries."""

    def load(self, path: Path) -> dict[str, Any]:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ConfigurationError("YAML config must contain a top-level mapping")
        return cast(dict[str, Any], raw)
