"""Async API Key Validator with HMAC-SHA256 signature verification."""

import asyncio
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from .exceptions import (
    InvalidSignatureError,
    KeyExpiredError,
    ValidationError,
)


class AsyncAPIKeyValidator:
    """Async validator for API keys using HMAC-SHA256 signatures."""

    def __init__(
        self,
        validation_window_minutes: int = 360,
        clock_skew_tolerance_seconds: int = 60,
    ):
        """Initialize the validator.

        Args:
            validation_window_minutes: Time window for key validation in minutes (default: 360/6 hours)
            clock_skew_tolerance_seconds: Clock skew tolerance in seconds (default: 60)
        """
        self.validation_window = timedelta(minutes=validation_window_minutes)
        self.clock_skew_tolerance = clock_skew_tolerance_seconds
        self._cache: Dict[str, Tuple[bool, float]] = {}
        self._cache_ttl = 300  # 5 minutes

    async def validate(
        self,
        key: str,
        signature: str,
        secret: str,
        timestamp: Optional[int] = None,
        use_cache: bool = True,
    ) -> bool:
        """Validate API key signature.

        Args:
            key: API key string
            signature: HMAC-SHA256 signature in hex format
            secret: Secret key for HMAC verification
            timestamp: Unix timestamp (uses current time if not provided)
            use_cache: Whether to use cached validation results

        Returns:
            True if signature is valid and within time window

        Raises:
            InvalidSignatureError: If signature doesn't match
            KeyExpiredError: If key is outside validation window
            ValidationError: If validation fails for any other reason
        """
        try:
            # Check cache
            if use_cache:
                cache_key = f"{key}:{signature}"
                if cache_key in self._cache:
                    is_valid, cache_time = self._cache[cache_key]
                    if time.time() - cache_time < self._cache_ttl:
                        return is_valid

            # Use current time if not provided
            if timestamp is None:
                timestamp = int(time.time())

            # Check timestamp validity
            await self._validate_timestamp(timestamp)

            # Verify signature
            await self._verify_signature(key, signature, secret)

            # Cache result
            if use_cache:
                cache_key = f"{key}:{signature}"
                self._cache[cache_key] = (True, time.time())

            return True

        except (InvalidSignatureError, KeyExpiredError):
            raise
        except Exception as e:
            raise ValidationError(f"Validation failed: {str(e)}") from e

    async def _validate_timestamp(self, timestamp: int) -> None:
        """Validate timestamp is within acceptable window.

        Args:
            timestamp: Unix timestamp to validate

        Raises:
            KeyExpiredError: If timestamp is outside window
        """
        await asyncio.sleep(0)  # Yield to event loop
        current_time = time.time()
        age = current_time - timestamp

        # Check if too old
        max_age = self.validation_window.total_seconds()
        if age > max_age + self.clock_skew_tolerance:
            raise KeyExpiredError(
                f"Key expired. Age: {age}s, Max: {max_age}s"
            )

        # Check if in future (clock skew)
        if age < -self.clock_skew_tolerance:
            raise KeyExpiredError(
                f"Key timestamp is in future. Skew: {-age}s"
            )

    async def _verify_signature(
        self,
        key: str,
        provided_signature: str,
        secret: str,
    ) -> None:
        """Verify HMAC-SHA256 signature using constant-time comparison.

        Args:
            key: API key string
            provided_signature: Signature to verify (hex string)
            secret: Secret key for HMAC

        Raises:
            InvalidSignatureError: If signature doesn't match
        """
        await asyncio.sleep(0)  # Yield to event loop

        # Calculate expected signature
        message = key.encode()
        secret_bytes = secret.encode()
        expected_signature = hmac.new(
            secret_bytes,
            message,
            hashlib.sha256
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected_signature, provided_signature):
            raise InvalidSignatureError(
                "HMAC signature verification failed"
            )

    async def batch_validate(
        self,
        validations: list[Dict[str, str]],
    ) -> list[bool]:
        """Validate multiple keys concurrently.

        Args:
            validations: List of dicts with 'key', 'signature', and 'secret'

        Returns:
            List of validation results (True/False for each)
        """
        tasks = [
            self.validate(
                validation["key"],
                validation["signature"],
                validation["secret"],
            )
            for validation in validations
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [not isinstance(r, Exception) for r in results]

    def clear_cache(self) -> None:
        """Clear the validation cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {"cache_size": len(self._cache)}
