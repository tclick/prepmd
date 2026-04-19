"""Composite validation pipeline (Chain of Responsibility)."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.config.validators.compatibility import CompatibilityValidator
from prepmd.config.validators.ensemble import EnsembleValidator
from prepmd.config.validators.pdb_input import PDBInputValidator
from prepmd.config.validators.restraint import RestraintValidator
from prepmd.config.validators.temperature import TemperatureValidator


class ValidationPipeline:
    """Run a sequence of validators against a project configuration.

    Validators are executed in insertion order.  The first failure raises
    immediately so that the caller receives one actionable error at a time.

    Parameters
    ----------
    validators : list[BaseValidator] | None
        Ordered list of validators to apply.  When *None* the default set
        (temperature, ensemble, restraint, compatibility) is used.
    """

    def __init__(self, validators: list[BaseValidator] | None = None) -> None:
        self._validators: list[BaseValidator] = (
            validators
            if validators is not None
            else [
                TemperatureValidator(),
                PDBInputValidator(),
                EnsembleValidator(),
                RestraintValidator(),
                CompatibilityValidator(),
            ]
        )

    def validate(self, config: ProjectConfig) -> None:
        """Run all validators in order; raise on the first failure."""
        for validator in self._validators:
            validator.validate(config)
