"""Async API Key Validator with HMAC-SHA256 signature verification."""

import asyncio
import hashlib
import hmac
import time
from collections import OrderedDict
from datetime import timedelta
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exceptions import (
    InvalidSignatureError,
    KeyExpiredError,
    ValidationError,
)

# SECURITY: the signed message includes the timestamp so that a captured
# request cannot be replayed beyond its validity window.  Clients must sign
# ``"{key}:{timestamp}"`` (see ``sign_request``).
SIGNATURE_MESSAGE_SEPARATOR = ":"


def build_signature_message(key: str, timestamp: int) -> str:
    """Return the canonical message that is fed into the HMAC.

    Includes the timestamp so signatures are bound to a point in time and
    cannot be replayed outside the validation window.
    """
    return f"{key}{SIGNATURE_MESSAGE_SEPARATOR}{timestamp}"


def sign_request(key: str, secret: str, timestamp: int) -> str:
    """Compute the HMAC-SHA256 hex signature for ``(key, timestamp)``.

    Provided as the reference implementation clients should use.
    """
    message = build_signature_message(key, timestamp)
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


class AsyncAPIKeyValidator:
    """Async validator for API keys using HMAC-SHA256 signatures."""

    #: Maximum number of entries kept in the validation cache.  Bounds memory
    #: usage against an attacker flooding validations with unique signatures.
    MAX_CACHE_SIZE = 10_000

    def __init__(
        self,
        validation_window_minutes: int = 360,
        clock_skew_tolerance_seconds: int = 60,
        cache_ttl_seconds: int = 300,
        max_cache_size: Optional[int] = None,
    ):
        """Initialize the validator.

        Args:
            validation_window_minutes: Time window for key validation in minutes (default: 360/6 hours)
            clock_skew_tolerance_seconds: Clock skew tolerance in seconds (default: 60)
            cache_ttl_seconds: TTL for cached *successful* validations.
            max_cache_size: Upper bound on cache entries (LRU eviction).
        """
        self.validation_window = timedelta(minutes=validation_window_minutes)
        self.clock_skew_tolerance = clock_skew_tolerance_seconds
        self._cache_ttl = cache_ttl_seconds
        self._max_cache_size = (
            self.MAX_CACHE_SIZE if max_cache_size is None else max_cache_size
        )
        # OrderedDict gives O(1) LRU eviction; plain dict did not bound growth.
        self._cache: "OrderedDict[str, float]" = OrderedDict()

    async def validate(
        self,
        key: str,
        signature: str,
        secret: str,
        timestamp: Optional[int] = None,
        use_cache: bool = True,
    ) -> bool:
        """Validate API key signature.

        The signature must be an HMAC-SHA256 over ``"{key}:{timestamp}"``
        (see :func:`sign_request`).  Binding the timestamp into the signed
        message prevents replay of a captured request beyond its window.

        Args:
            key: API key string
            signature: HMAC-SHA256 signature in hex format
            secret: Secret key for HMAC verification
            timestamp: Unix timestamp used when the signature was created
                (uses current time if not provided)
            use_cache: Whether to use cached validation results

        Returns:
            True if signature is valid and within time window

        Raises:
            InvalidSignatureError: If signature doesn't match
            KeyExpiredError: If key is outside validation window
            ValidationError: If validation fails for any other reason
        """
        try:
            # Use current time if not provided
            if timestamp is None:
                timestamp = int(time.time())

            # Check cache.  Keyed on (key, signature, timestamp) so a cached
            # approval cannot outlive the timestamp it was bound to, and
            # revoked/rotated secrets re-verify after TTL expiry.
            cache_key: Optional[str] = None
            if use_cache:
                cache_key = f"{key}:{signature}:{timestamp}"
                cached_at = self._cache.get(cache_key)
                if cached_at is not None:
                    if time.time() - cached_at < self._cache_ttl:
                        # Mark as most-recently-used for LRU ordering.
                        self._cache.move_to_end(cache_key)
                        return True
                    del self._cache[cache_key]

            # Check timestamp validity
            await self._validate_timestamp(timestamp)

            # Verify signature (bound to timestamp -> replay-resistant)
            await self._verify_signature(key, signature, secret, timestamp)

            # Cache only successful validations, with bounded LRU eviction.
            if use_cache and cache_key is not None:
                self._cache[cache_key] = time.time()
                self._cache.move_to_end(cache_key)
                while len(self._cache) > self._max_cache_size:
                    self._cache.popitem(last=False)

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
        timestamp: int,
    ) -> None:
        """Verify HMAC-SHA256 signature using constant-time comparison.

        The signed message is ``"{key}:{timestamp}"`` so that a captured
        signature cannot be replayed with a different (still-valid) timestamp.

        Args:
            key: API key string
            provided_signature: Signature to verify (hex string)
            secret: Secret key for HMAC
            timestamp: Unix timestamp that was included in the signed message

        Raises:
            InvalidSignatureError: If signature doesn't match
        """
        await asyncio.sleep(0)  # Yield to event loop

        # Calculate expected signature over key + timestamp
        message = build_signature_message(key, timestamp).encode()
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
        validations: Sequence[Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Validate multiple keys concurrently.

        Unlike the previous behaviour, individual failures no longer collapse
        into an opaque ``False``; each result carries the error type/message
        so callers can distinguish expired keys from bad signatures.

        Args:
            validations: Sequence of mappings with 'key', 'signature',
                'secret' and optionally 'timestamp'.

        Returns:
            List of result dicts: ``{"valid": bool, "error": str|None}``
            in the same order as the input.
        """
        tasks = [
            self.validate(
                validation["key"],
                validation["signature"],
                validation["secret"],
                timestamp=validation.get("timestamp"),
            )
            for validation in validations
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            {"valid": True, "error": None}
            if not isinstance(r, BaseException)
            else {"valid": False, "error": type(r).__name__}
            for r in results
        ]

    def invalidate_key(self, key: str) -> int:
        """Drop all cached validations for ``key`` (e.g. after rotation).

        Returns:
            Number of cache entries removed.
        """
        prefix = f"{key}:"
        stale = [ck for ck in self._cache if ck.startswith(prefix)]
        for ck in stale:
            del self._cache[ck]
        return len(stale)

    def clear_cache(self) -> None:
        """Clear the validation cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self._max_cache_size,
        }
