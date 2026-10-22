"""Optional HashiCorp Vault client for storing and retrieving API key secrets.

This module is intentionally import-safe: ``hvac`` is an optional dependency
(extras_require ``vault``), so importing :mod:`vault_integration` never fails
even when ``hvac`` is not installed.  Instantiating :class:`VaultClient`
without the dependency raises :class:`core.exceptions.VaultError`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.exceptions import VaultError

try:  # pragma: no cover - exercised via dependency-injection tests
    import hvac  # type: ignore

    _HVAC_AVAILABLE = True
except ImportError:  # pragma: no cover
    hvac = None  # type: ignore[assignment]
    _HVAC_AVAILABLE = False

logger = logging.getLogger(__name__)

__all__ = ["VaultClient"]


class VaultClient:
    """Thin wrapper around the hvac Vault client for secret storage.

    Args:
        url: Vault address (e.g. ``http://127.0.0.1:8200``).
        token: Vault authentication token.
        mount_point: KV secrets engine mount point (default ``"kv"``).
        namespace: Optional Vault Enterprise namespace.
        verify: TLS verification option passed to hvac.
        client: Pre-configured hvac client (dependency injection; mainly
            used in tests to avoid requiring a live Vault server).

    Raises:
        VaultError: If ``hvac`` is not installed and no client is injected,
            or if connection/authentication fails.
    """

    def __init__(
        self,
        url: str = "http://127.0.0.1:8200",
        token: Optional[str] = None,
        mount_point: str = "kv",
        namespace: Optional[str] = None,
        verify: Any = True,
        client: Optional[Any] = None,
    ) -> None:
        self.mount_point = mount_point

        if client is not None:
            self._client = client
            return

        if not _HVAC_AVAILABLE:
            raise VaultError(
                "hvac is required for Vault integration. "
                "Install with: pip install api-key-manager-pro[vault]"
            )
        if not token:
            raise VaultError("A Vault token is required to authenticate.")

        try:
            self._client = hvac.Client(
                url=url,
                token=token,
                namespace=namespace,
                verify=verify,
            )
            if not self._client.is_authenticated():
                raise VaultError("Vault authentication failed.")
        except VaultError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise VaultError(f"Failed to connect to Vault at {url}: {exc}") from exc

    @classmethod
    def from_settings(cls, settings: Any) -> "VaultClient":
        """Build a client from a settings object exposing VAULT_* attributes."""
        return cls(
            url=getattr(settings, "VAULT_ADDR", "http://127.0.0.1:8200"),
            token=getattr(settings, "VAULT_TOKEN", None),
            mount_point=getattr(settings, "VAULT_NAMESPACE", "kv"),
        )

    def store_secret(self, path: str, data: Dict[str, Any]) -> None:
        """Store a secret at ``path`` in the configured KV mount.

        Raises:
            VaultError: On any backend failure.
        """
        try:
            self._client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=data,
                mount_point=self.mount_point,
            )
            logger.info("Stored secret at vault path: %s", path)
        except Exception as exc:  # noqa: BLE001
            raise VaultError(f"Failed to store secret at {path!r}: {exc}") from exc

    def read_secret(self, path: str) -> Dict[str, Any]:
        """Read a secret from ``path``.

        Raises:
            VaultError: On backend failure.
            KeyError: If the secret does not exist (propagated from hvac).
        """
        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point,
                raise_on_deleted_version=True,
            )
            return response["data"]["data"]
        except KeyError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VaultError(f"Failed to read secret at {path!r}: {exc}") from exc

    def delete_secret(self, path: str) -> None:
        """Delete a secret at ``path``.

        Raises:
            VaultError: On backend failure.
        """
        try:
            self._client.secrets.kv.v2.delete_metadata_or_cancel_delete(
                path=path,
                mount_point=self.mount_point,
            )
            logger.info("Deleted secret at vault path: %s", path)
        except Exception as exc:  # noqa: BLE001
            raise VaultError(
                f"Failed to delete secret at {path!r}: {exc}"
            ) from exc
