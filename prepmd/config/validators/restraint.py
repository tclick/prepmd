"""Restraint-related validation."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.exceptions import ValidationError


class RestraintValidator(BaseValidator):
    """Validate restraint-compatible values."""

    def validate(self, config: ProjectConfig) -> None:
        if config.simulation.replicas < 1:
            raise ValidationError("replicas must be >= 1")
