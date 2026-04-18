"""Engine compatibility validator."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.engines.factory import EngineFactory
from prepmd.exceptions import BoxShapeNotSupportedError, EngineError, ValidationError


class CompatibilityValidator(BaseValidator):
    """Validate engine/ensemble compatibility."""

    def validate(self, config: ProjectConfig) -> None:
        try:
            engine = EngineFactory.create(config.engine.name)
        except EngineError as exc:
            raise ValidationError(f"unsupported engine: {config.engine.name}") from exc
        allowed = engine.capabilities.supported_ensembles
        if config.simulation.ensemble not in allowed:
            raise ValidationError(f"ensemble {config.simulation.ensemble} is not supported by {config.engine.name}")
        if not engine.supports_box_shape(config.water_box.shape):
            raise BoxShapeNotSupportedError(
                f"Engine {config.engine.name} does not support box shape {config.water_box.shape!r}."
            )
