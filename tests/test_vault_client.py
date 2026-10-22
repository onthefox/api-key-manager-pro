"""Tests for vault_integration.VaultClient (hvac mocked - no server needed)."""

from unittest.mock import MagicMock

import pytest

from core.exceptions import VaultError
from vault_integration import VaultClient


@pytest.fixture
def mock_hvac_client() -> MagicMock:
    client = MagicMock()
    client.is_authenticated.return_value = True
    return client


class TestConstruction:
    def test_injected_client_skips_hvac(self, mock_hvac_client):
        vc = VaultClient(client=mock_hvac_client)
        assert vc._client is mock_hvac_client

    def test_missing_token_raises(self, monkeypatch):
        # Pretend hvac is available but no token supplied
        monkeypatch.setattr(
            "vault_integration.vault_client._HVAC_AVAILABLE", True, raising=False
        )
        with pytest.raises(VaultError):
            VaultClient(url="http://localhost:1", token=None)

    def test_hvac_unavailable_raises_actionable_error(self, monkeypatch):
        monkeypatch.setattr("vault_integration.vault_client._HVAC_AVAILABLE", False)
        with pytest.raises(VaultError, match="hvac is required"):
            VaultClient(token="t")


class TestSecretOperations:
    def test_store_secret_calls_kv_v2(self, mock_hvac_client):
        vc = VaultClient(client=mock_hvac_client, mount_point="secret")
        vc.store_secret("api-keys/k1", {"secret": "abc"})
        mock_hvac_client.secrets.kv.v2.create_or_update_secret.assert_called_once_with(
            path="api-keys/k1", secret={"secret": "abc"}, mount_point="secret"
        )

    def test_read_secret_returns_data(self, mock_hvac_client):
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"secret": "abc"}}
        }
        vc = VaultClient(client=mock_hvac_client)
        assert vc.read_secret("api-keys/k1") == {"secret": "abc"}

    def test_backend_failure_normalized_to_vault_error(self, mock_hvac_client):
        mock_hvac_client.secrets.kv.v2.create_or_update_secret.side_effect = RuntimeError(
            "boom"
        )
        vc = VaultClient(client=mock_hvac_client)
        with pytest.raises(VaultError, match="Failed to store secret"):
            vc.store_secret("p", {"a": 1})

    def test_delete_secret(self, mock_hvac_client):
        vc = VaultClient(client=mock_hvac_client)
        vc.delete_secret("api-keys/k1")
        mock_hvac_client.secrets.kv.v2.delete_metadata_or_cancel_delete.assert_called_once()
