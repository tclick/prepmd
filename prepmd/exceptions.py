"""Custom exception hierarchy for prepmd."""


class PrepMDError(Exception):
    """Base exception for all prepmd errors."""


class ConfigurationError(PrepMDError):
    """Raised when configuration is invalid or cannot be loaded."""


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""


class EngineError(PrepMDError):
    """Raised for engine selection and execution errors."""


class FileGenerationError(PrepMDError):
    """Raised when file generation fails."""


class StructureBuildError(PrepMDError):
    """Raised when directory structure creation fails."""


class PDBDownloadError(PrepMDError):
    """Raised when downloading a PDB structure fails."""


class PDBValidationError(ValidationError):
    """Raised when a PDB ID is invalid."""


class PDBMutualExclusivityError(ValidationError):
    """Raised when PDB input methods are both specified or both missing."""
