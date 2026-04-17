"""prepmd package."""

from importlib.metadata import PackageNotFoundError, version

from prepmd.config.models import ProjectConfig

try:
    __version__ = version("prepmd")
except PackageNotFoundError:  # pragma: no cover - local editable without metadata
    __version__ = "0.0.0"

__all__ = ["ProjectConfig", "__version__"]
