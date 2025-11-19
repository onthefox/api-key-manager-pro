"""Settings configuration for API Key Manager Pro."""

import os
from typing import Optional


class Settings:
    """Application settings."""

    # Validation settings
    VALIDATION_WINDOW_MINUTES: int = int(
        os.getenv("VALIDATION_WINDOW_MINUTES", "360")
    )
    CLOCK_SKEW_TOLERANCE_SECONDS: int = int(
        os.getenv("CLOCK_SKEW_TOLERANCE_SECONDS", "60")
    )

    # Flask settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5000"))

    # Database settings
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Vault settings
    VAULT_ENABLED: bool = os.getenv("VAULT_ENABLED", "False").lower() == "true"
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
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = (
        os.getenv("RATE_LIMIT_ENABLED", "False").lower() == "true"
    )
    RATE_LIMIT_PER_MINUTE: int = int(
        os.getenv("RATE_LIMIT_PER_MINUTE", "100")
    )

    @classmethod
    def to_dict(cls) -> dict:
        """Convert settings to dictionary (excluding secrets)."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and key.isupper()
            and key not in ["SECRET_KEY", "VAULT_TOKEN"]
        }
