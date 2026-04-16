"""Engine compatibility validator."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.exceptions import ValidationError


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
            raise ValidationError(
                f"ensemble {config.simulation.ensemble} is not supported by {config.engine.name}"
            )
