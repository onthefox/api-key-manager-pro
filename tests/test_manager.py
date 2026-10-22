"""Tests for core.manager.KeyManager."""

import time

import pytest

from core.exceptions import InvalidSignatureError, KeyNotFoundError, KeyRevokedError
from core.manager import KeyManager
from core.validator import sign_request

SECRET = "s3cr3t"


def _ts(offset: int = 0) -> int:
    return int(time.time()) + offset


@pytest.fixture
def manager() -> KeyManager:
    mgr = KeyManager()
    yield mgr
    mgr.clear()


class TestCreateKey:
    @pytest.mark.asyncio
    async def test_create_returns_redacted_record(self, manager):
        record = await manager.create_key("k1", SECRET)
        assert record["key_id"] == "k1"
        assert record["secret"] == "***REDACTED***"
        assert record["active"] is True

    @pytest.mark.asyncio
    async def test_duplicate_creation_rejected(self, manager):
        await manager.create_key("k1", SECRET)
        with pytest.raises(ValueError):
            await manager.create_key("k1", "other")

    @pytest.mark.asyncio
    async def test_created_at_is_timezone_aware(self, manager):
        record = await manager.create_key("k1", SECRET)
        # tz-aware ISO timestamps end with an offset like +00:00
        assert "+00:00" in record["created_at"]


class TestValidateKey:
    @pytest.mark.asyncio
    async def test_valid_flow(self, manager):
        await manager.create_key("k1", SECRET)
        ts = _ts()
        sig = sign_request("k1", SECRET, ts)
        assert await manager.validate_key("k1", sig, timestamp=ts) is True
        rec = await manager.get_key("k1")
        assert rec["last_used"] is not None

    @pytest.mark.asyncio
    async def test_unknown_key_raises_not_found(self, manager):
        with pytest.raises(KeyNotFoundError):
            await manager.validate_key("missing", "sig")

    @pytest.mark.asyncio
    async def test_revoked_key_raises_revoked(self, manager):
        await manager.create_key("k1", SECRET)
        await manager.revoke_key("k1")
        with pytest.raises(KeyRevokedError):
            await manager.validate_key("k1", "whatever")

    @pytest.mark.asyncio
    async def test_bad_signature_raises(self, manager):
        await manager.create_key("k1", SECRET)
        with pytest.raises(InvalidSignatureError):
            await manager.validate_key("k1", "a" * 64, timestamp=_ts())


class TestRevokeKey:
    @pytest.mark.asyncio
    async def test_revoke_purges_validator_cache(self, manager):
        await manager.create_key("k1", SECRET)
        ts = _ts()
        sig = sign_request("k1", SECRET, ts)
        await manager.validate_key("k1", sig, timestamp=ts)
        assert manager.validator.get_cache_stats()["cache_size"] == 1

        await manager.revoke_key("k1")
        assert manager.validator.get_cache_stats()["cache_size"] == 0

    @pytest.mark.asyncio
    async def test_revoke_unknown_raises(self, manager):
        with pytest.raises(KeyNotFoundError):
            await manager.revoke_key("nope")


class TestGetAndList:
    @pytest.mark.asyncio
    async def test_get_key_redacts_secret(self, manager):
        await manager.create_key("k1", SECRET)
        rec = await manager.get_key("k1")
        assert rec["secret"] == "***REDACTED***"

    @pytest.mark.asyncio
    async def test_get_key_copy_does_not_mutate_store(self, manager):
        await manager.create_key("k1", SECRET)
        rec = await manager.get_key("k1")
        rec["metadata"]["injected"] = True
        fresh = await manager.get_key("k1")
        assert "injected" not in fresh["metadata"]

    @pytest.mark.asyncio
    async def test_list_keys_active_only(self, manager):
        await manager.create_key("k1", SECRET)
        await manager.create_key("k2", SECRET)
        await manager.revoke_key("k2")
        active = manager.list_keys()
        all_keys = manager.list_keys(active_only=False)
        assert [k["key_id"] for k in active] == ["k1"]
        assert len(all_keys) == 2
        assert all(k["secret"] == "***REDACTED***" for k in all_keys)


class TestBatchValidate:
    @pytest.mark.asyncio
    async def test_reports_per_item_errors(self, manager):
        await manager.create_key("k1", SECRET)
        ts = _ts()
        validations = [
            {"key_id": "k1", "signature": sign_request("k1", SECRET, ts), "timestamp": ts},
            {"key_id": "k1", "signature": "z" * 64, "timestamp": ts},
            {"key_id": "ghost", "signature": "y" * 64},
        ]
        results = await manager.batch_validate(validations)
        assert results[0] == {"key_id": "k1", "valid": True, "error": None}
        assert results[1]["valid"] is False
        assert results[1]["error"] == "InvalidSignatureError"
        assert results[2]["valid"] is False
        assert results[2]["error"] == "KeyNotFoundError"


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_actions_are_audited(self, manager):
        await manager.create_key("k1", SECRET)
        ts = _ts()
        await manager.validate_key("k1", sign_request("k1", SECRET, ts), timestamp=ts)
        await manager.revoke_key("k1")
        actions = [e["action"] for e in manager.get_audit_log()]
        assert actions == ["key_created", "key_validated", "key_revoked"]

    @pytest.mark.asyncio
    async def test_audit_log_copy_is_detached(self, manager):
        await manager.create_key("k1", SECRET)
        log = manager.get_audit_log()
        log.append({"fake": True})
        assert len(manager.get_audit_log()) == 1
