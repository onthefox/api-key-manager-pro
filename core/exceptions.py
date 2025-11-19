"""Custom exceptions for API Key Manager Pro."""


class APIKeyManagerException(Exception):
    """Base exception for all API Key Manager errors."""
    pass


class InvalidSignatureError(APIKeyManagerException):
    """Raised when HMAC signature verification fails."""
    pass


class KeyExpiredError(APIKeyManagerException):
    """Raised when API key has expired based on validation window."""
    pass


class KeyNotFoundError(APIKeyManagerException):
    """Raised when requested API key is not found in the system."""
    pass


class ValidationError(APIKeyManagerException):
    """Raised when API key validation fails for any reason."""
    pass


class ConfigurationError(APIKeyManagerException):
    """Raised when configuration is invalid or missing."""
    pass


class VaultError(APIKeyManagerException):
    """Raised when Vault integration fails."""
    pass


class RateLimitExceededError(APIKeyManagerException):
    """Raised when rate limit is exceeded for API key validation."""
    pass


class EncryptionError(APIKeyManagerException):
    """Raised when encryption or decryption fails."""
    pass
