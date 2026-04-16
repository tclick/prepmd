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
