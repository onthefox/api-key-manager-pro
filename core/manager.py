"""API Key Manager for batch operations and key lifecycle management."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .exceptions import KeyNotFoundError
from .validator import AsyncAPIKeyValidator

logger = logging.getLogger(__name__)


class KeyManager:
    """Manages API keys lifecycle including creation, validation, and revocation."""

    def __init__(self, validator: Optional[AsyncAPIKeyValidator] = None):
        """Initialize Key Manager.

        Args:
            validator: AsyncAPIKeyValidator instance. If None, creates a new one.
        """
        self.validator = validator or AsyncAPIKeyValidator()
        self._keys: Dict[str, Dict] = {}
        self._audit_log: List[Dict] = []

    async def create_key(
        self,
        key_id: str,
        secret: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Create a new API key.

        Args:
            key_id: Unique key identifier
            secret: Secret for HMAC verification
            metadata: Optional metadata for the key

        Returns:
            Created key record
        """
        await asyncio.sleep(0)

        key_record = {
            "key_id": key_id,
            "secret": secret,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "active": True,
            "last_used": None,
        }

        self._keys[key_id] = key_record
        self._log_audit("key_created", key_id)
        logger.info(f"Key created: {key_id}")

        return key_record

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

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
        self._log_audit("key_revoked", key_id)
        logger.info(f"Key revoked: {key_id}")

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
            signature: HMAC-SHA256 signature
            timestamp: Optional timestamp

        Returns:
            True if valid

        Raises:
            KeyNotFoundError: If key doesn't exist
        """
        if key_id not in self._keys:
            raise KeyNotFoundError(f"Key not found: {key_id}")

        key_record = self._keys[key_id]
        if not key_record["active"]:
            raise KeyNotFoundError(f"Key is revoked: {key_id}")

        result = await self.validator.validate(
            key_id,
            signature,
            key_record["secret"],
            timestamp=timestamp,
        )

        if result:
            self._keys[key_id]["last_used"] = datetime.utcnow().isoformat()
            self._log_audit("key_validated", key_id)

        return result

    async def get_key(self, key_id: str) -> Dict:
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

        key_record = self._keys[key_id].copy()
        key_record["secret"] = "***REDACTED***"
        return key_record

    async def batch_validate(
        self,
        validations: List[Dict],
    ) -> List[Dict]:
        """Validate multiple keys concurrently.

        Args:
            validations: List of dicts with 'key_id', 'signature'

        Returns:
            List of validation results
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
        return [
            {"key_id": v["key_id"], "valid": not isinstance(r, Exception)}
            for v, r in zip(validations, results)
        ]

    def list_keys(self, active_only: bool = True) -> List[Dict]:
        """List all keys.

        Args:
            active_only: If True, only return active keys

        Returns:
            List of key records (secrets redacted)
        """
        keys = [
            {**k, "secret": "***REDACTED***"}
            for k in self._keys.values()
            if not active_only or k["active"]
        ]
        return keys

    def get_audit_log(self) -> List[Dict]:
        """Get audit log entries.

        Returns:
            Audit log
        """
        return self._audit_log.copy()

    def _log_audit(self, action: str, key_id: str) -> None:
        """Log an audit event.

        Args:
            action: Action performed
            key_id: Key affected
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "key_id": key_id,
        }
        self._audit_log.append(entry)
        logger.debug(f"Audit: {action} - {key_id}")

    def clear(self) -> None:
        """Clear all keys and audit logs."""
        self._keys.clear()
        self._audit_log.clear()
