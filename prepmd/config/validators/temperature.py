"""Temperature validation rules."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.exceptions import ValidationError


class TemperatureValidator(BaseValidator):
    """Validate simulation temperature range."""

    def validate(self, config: ProjectConfig) -> None:
        if not 0.0 < config.simulation.temperature < 1000.0:
            raise ValidationError("temperature must be between 0 and 1000 K")
