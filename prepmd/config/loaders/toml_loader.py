"""TOML configuration loader."""

import tomllib
from pathlib import Path
from typing import Any

from prepmd.config.loaders.base import BaseConfigLoader


class TOMLConfigLoader(BaseConfigLoader):
    """Load TOML files into dictionaries."""

    def load(self, path: Path) -> dict[str, Any]:
        return tomllib.loads(path.read_text(encoding="utf-8"))
