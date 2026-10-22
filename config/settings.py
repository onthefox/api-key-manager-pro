"""Settings configuration for API Key Manager Pro."""

import logging
import os
import secrets
from typing import Optional

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    """Read an int from the environment, falling back to *default*.

    Never crashes the process at import time on a malformed value; logs a
    warning and uses the safe default instead.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid integer for %s=%r; using default %d", name, raw, default
        )
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a bool from the environment ('1/true/yes/on', case-insensitive)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Application settings."""

    # Validation settings
    VALIDATION_WINDOW_MINUTES: int = _env_int("VALIDATION_WINDOW_MINUTES", 360)
    CLOCK_SKEW_TOLERANCE_SECONDS: int = _env_int("CLOCK_SKEW_TOLERANCE_SECONDS", 60)

    # Flask settings
    DEBUG: bool = _env_bool("DEBUG")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = _env_int("PORT", 5000)

    # Database settings
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Vault settings
    VAULT_ENABLED: bool = _env_bool("VAULT_ENABLED")
    VAULT_ADDR: str = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
    VAULT_TOKEN: Optional[str] = os.getenv("VAULT_TOKEN")
    VAULT_NAMESPACE: str = os.getenv("VAULT_NAMESPACE", "kv")

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Cache settings
    CACHE_TTL_SECONDS: int = _env_int("CACHE_TTL_SECONDS", 300)

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = _env_bool("RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = _env_int("RATE_LIMIT_PER_MINUTE", 100)

    @classmethod
    def validate(cls) -> None:
        """Fail fast on unsafe production configuration.

        SECURITY: previously SECRET_KEY defaulted to the well-known string
        ``"dev-secret-key"``, which is guessable by anyone reading the source.
        Now an explicit secret is required outside DEBUG mode; in DEBUG a
        random per-process key is generated (sessions won't survive restarts,
        which is acceptable for local development only).

        Raises:
            ConfigurationError: If a required setting is missing or invalid.
        """
        from core.exceptions import ConfigurationError

        if not cls.SECRET_KEY:
            if cls.DEBUG:
                cls.SECRET_KEY = secrets.token_hex(32)
                logger.warning(
                    "SECRET_KEY not set; generated an ephemeral key (DEBUG only)."
                )
            else:
                raise ConfigurationError(
                    "SECRET_KEY must be set in the environment when DEBUG is off."
                )

        if cls.VALIDATION_WINDOW_MINUTES <= 0:
            raise ConfigurationError("VALIDATION_WINDOW_MINUTES must be positive.")
        if cls.CACHE_TTL_SECONDS < 0:
            raise ConfigurationError("CACHE_TTL_SECONDS must be >= 0.")

    @classmethod
    def to_dict(cls) -> dict:
        """Convert settings to dictionary (excluding secrets)."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_")
            and key.isupper()
            and key not in ("SECRET_KEY", "VAULT_TOKEN")
        }
