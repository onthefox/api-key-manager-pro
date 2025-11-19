"""API Key Manager Pro - Core module.

Async-first API key validation and management system with HMAC-SHA256 signatures.
"""

from .exceptions import (
    APIKeyManagerException,
    InvalidSignatureError,
    KeyExpiredError,
    KeyNotFoundError,
    ValidationError,
)
from .manager import KeyManager
from .validator import AsyncAPIKeyValidator

__version__ = "1.0.0"
__all__ = [
    "APIKeyManagerException",
    "InvalidSignatureError",
    "KeyExpiredError",
    "KeyNotFoundError",
    "ValidationError",
    "AsyncAPIKeyValidator",
    "KeyManager",
]
