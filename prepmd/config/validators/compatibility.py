"""Engine compatibility validator."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.engines.factory import EngineFactory
from prepmd.exceptions import BoxShapeNotSupportedError, ValidationError


class CompatibilityValidator(BaseValidator):
    """Validate engine/ensemble compatibility."""

    _engine_ensemble_map = {
        "amber": {"NVT", "NPT", "NVE"},
        "gromacs": {"NVT", "NPT", "NVE"},
        "namd": {"NVT", "NPT"},
        "charmm": {"NVT", "NPT"},
        "openmm": {"NVT", "NPT", "NVE"},
    }

    def validate(self, config: ProjectConfig) -> None:
        allowed = self._engine_ensemble_map.get(config.engine.name.lower())
        if allowed is None:
            raise ValidationError(f"unsupported engine: {config.engine.name}")
        if config.simulation.ensemble not in allowed:
            raise ValidationError(f"ensemble {config.simulation.ensemble} is not supported by {config.engine.name}")
        engine = EngineFactory.create(config.engine.name)
        if not engine.supports_box_shape(config.water_box.shape):
            raise BoxShapeNotSupportedError(
                f"Engine {config.engine.name} does not support box shape {config.water_box.shape!r}."
            )
