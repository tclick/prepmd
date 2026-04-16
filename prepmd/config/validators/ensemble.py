"""Ensemble validation rules."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.exceptions import ValidationError


class EnsembleValidator(BaseValidator):
    """Validate supported ensembles."""

    _allowed = {"NVT", "NPT", "NVE"}

    def validate(self, config: ProjectConfig) -> None:
        if config.simulation.ensemble not in self._allowed:
            raise ValidationError(
                f"ensemble must be one of {sorted(self._allowed)}"
            )
