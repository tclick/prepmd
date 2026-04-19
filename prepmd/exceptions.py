"""Custom exception hierarchy for prepmd."""


class PrepMDError(Exception):
    """Base exception for all prepmd errors."""


class ConfigurationError(PrepMDError):
    """Raised when configuration is invalid or cannot be loaded."""


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""


class ValidationErrorGroup(ExceptionGroup):
    """Raised when configuration validation returns multiple errors."""


class EngineError(PrepMDError):
    """Raised for engine selection and execution errors."""


class FileGenerationError(PrepMDError):
    """Raised when file generation fails."""


class StructureBuildError(PrepMDError):
    """Raised when directory structure creation fails."""


class SetupPlanError(PrepMDError):
    """Raised when deterministic setup planning fails."""


class SetupApplyError(PrepMDError):
    """Raised when applying a setup plan fails."""


class PDBDownloadError(PrepMDError):
    """Raised when downloading a PDB structure fails."""


class PDBValidationError(ValidationError):
    """Raised when a PDB ID is invalid."""


class PDBMutualExclusivityError(ValidationError):
    """Raised when PDB input methods are both specified or both missing."""


class BoxGeometryError(ValidationError):
    """Raised for invalid water-box geometry settings."""


class InvalidBoxDimensionsError(BoxGeometryError):
    """Raised when one or more box dimensions are invalid."""


class BoxShapeNotSupportedError(BoxGeometryError):
    """Raised when an engine does not support the requested box shape."""


class PDBParseError(PrepMDError):
    """Raised when a PDB file cannot be parsed or contains no atoms."""
