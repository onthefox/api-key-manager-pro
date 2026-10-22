"""API Key Manager for batch operations and key lifecycle management."""

import asyncio
import copy
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .exceptions import KeyNotFoundError, KeyRevokedError
from .validator import AsyncAPIKeyValidator

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    """Timezone-aware UTC timestamp (datetime.utcnow() is deprecated)."""
    return datetime.now(timezone.utc).isoformat()


class KeyManager:
    """Manages API keys lifecycle including creation, validation, and revocation."""

    def __init__(self, validator: Optional[AsyncAPIKeyValidator] = None):
        """Initialize Key Manager.

        Args:
            validator: AsyncAPIKeyValidator instance. If None, creates a new one.
        """
        self.validator = validator or AsyncAPIKeyValidator()
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._audit_log: List[Dict[str, Any]] = []

    async def create_key(
        self,
        key_id: str,
        secret: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new API key.

        The returned record has the secret redacted; the caller must supply
        the secret out-of-band to the key owner (it is never echoed back by
        this API, preventing accidental leakage into logs/responses).

        Args:
            key_id: Unique key identifier
            secret: Secret for HMAC verification
            metadata: Optional metadata for the key

        Returns:
            Created key record with the secret redacted.

        Raises:
            ValueError: If a key with the same id already exists.
        """
        await asyncio.sleep(0)

        if key_id in self._keys:
            raise ValueError(f"Key already exists: {key_id}")

        key_record = {
            "key_id": key_id,
            "secret": secret,
            "created_at": _utcnow_iso(),
            "metadata": metadata or {},
            "active": True,
            "last_used": None,
        }

        self._keys[key_id] = key_record
        self._log_audit("key_created", key_id)
        logger.info("Key created: %s", key_id)

        return self._redact(key_record)

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Also purges any cached validations so revocation takes effect
        immediately rather than after the cache TTL.

        Args:
            key_id: Key to revoke

        Returns:
            True if successful

        Raises:
            KeyNotFoundError: If key doesn't exist
        """
        await asyncio.sleep(0)

        if key_id not in self._keys:
            raise KeyNotFoundError(f"Key not found: {key_id}")

        self._keys[key_id]["active"] = False
        self.validator.invalidate_key(key_id)
        self._log_audit("key_revoked", key_id)
        logger.info("Key revoked: %s", key_id)

        return True

    async def validate_key(
        self,
        key_id: str,
        signature: str,
        timestamp: Optional[int] = None,
    ) -> bool:
        """Validate an API key signature.

        Args:
            key_id: Key to validate
            signature: HMAC-SHA256 signature over "{key_id}:{timestamp}"
            timestamp: Timestamp used when the signature was created

        Returns:
            True if valid

        Raises:
            KeyNotFoundError: If key doesn't exist
            KeyRevokedError: If the key exists but has been revoked
        """
        if key_id not in self._keys:
            raise KeyNotFoundError(f"Key not found: {key_id}")

        key_record = self._keys[key_id]
        if not key_record["active"]:
            # Distinct from "not found": callers can map this to 401 vs 404
            # and it no longer masks revocation as a missing key.
            raise KeyRevokedError(f"Key is revoked: {key_id}")

        result = await self.validator.validate(
            key_id,
            signature,
            key_record["secret"],
            timestamp=timestamp,
        )

        if result:
            self._keys[key_id]["last_used"] = _utcnow_iso()
            self._log_audit("key_validated", key_id)

        return result

    @staticmethod
    def _redact(key_record: Dict[str, Any]) -> Dict[str, Any]:
        """Return a deep copy of a key record with the secret redacted.

        Deep copy prevents callers from mutating nested structures (e.g.
        ``metadata``) of the record held in the internal store.
        """
        redacted = copy.deepcopy(key_record)
        redacted["secret"] = "***REDACTED***"
        return redacted

    async def get_key(self, key_id: str) -> Dict[str, Any]:
        """Get key details (without exposing secret).

        Args:
            key_id: Key to retrieve

        Returns:
            Key record (secret redacted)

        Raises:
            KeyNotFoundError: If key doesn't exist
        """
        await asyncio.sleep(0)

        if key_id not in self._keys:
            raise KeyNotFoundError(f"Key not found: {key_id}")

        return self._redact(self._keys[key_id])

    async def batch_validate(
        self,
        validations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Validate multiple keys concurrently.

        Failures are reported per-item with an ``error`` field instead of
        being silently collapsed into ``valid: False``.

        Args:
            validations: List of dicts with 'key_id', 'signature' and
                optional 'timestamp'.

        Returns:
            List of result dicts:
            ``{"key_id": str, "valid": bool, "error": str|None}``
        """
        tasks = [
            self.validate_key(
                validation["key_id"],
                validation["signature"],
                validation.get("timestamp"),
            )
            for validation in validations
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        output: List[Dict[str, Any]] = []
        for v, r in zip(validations, results):
            if isinstance(r, BaseException):
                logger.debug(
                    "Batch validation failed for %s: %s", v["key_id"], r
                )
                output.append(
                    {"key_id": v["key_id"], "valid": False, "error": type(r).__name__}
                )
            else:
                output.append({"key_id": v["key_id"], "valid": r, "error": None})
        return output

    def list_keys(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all keys.

        Args:
            active_only: If True, only return active keys

        Returns:
            List of key records (secrets redacted)
        """
        return [
            self._redact(k)
            for k in self._keys.values()
            if not active_only or k["active"]
        ]

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit log entries.

        Returns:
            Audit log (shallow copy)
        """
        return list(self._audit_log)

    def _log_audit(self, action: str, key_id: str) -> None:
        """Log an audit event.

        Args:
            action: Action performed
            key_id: Key affected
        """
        entry = {
            "timestamp": _utcnow_iso(),
            "action": action,
            "key_id": key_id,
        }
        self._audit_log.append(entry)
        logger.debug("Audit: %s - %s", action, key_id)

    def clear(self) -> None:
        """Clear all keys and audit logs, and the validator cache."""
        self._keys.clear()
        self._audit_log.clear()
        self.validator.clear_cache()
