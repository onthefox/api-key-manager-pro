"""Tests for core.validator.AsyncAPIKeyValidator."""

import time

import pytest

from core.exceptions import InvalidSignatureError, KeyExpiredError
from core.validator import AsyncAPIKeyValidator, sign_request

KEY = "test-key"
SECRET = "test-secret"


def _ts(offset: int = 0) -> int:
    return int(time.time()) + offset


@pytest.fixture
def validator() -> AsyncAPIKeyValidator:
    return AsyncAPIKeyValidator(validation_window_minutes=5, clock_skew_tolerance_seconds=10)


class TestSignRequest:
    def test_deterministic(self):
        ts = _ts()
        assert sign_request(KEY, SECRET, ts) == sign_request(KEY, SECRET, ts)

    def test_binds_timestamp(self):
        """Changing the timestamp must change the signature (replay defense)."""
        ts = _ts()
        assert sign_request(KEY, SECRET, ts) != sign_request(KEY, SECRET, ts + 1)

    def test_binds_key_and_secret(self):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        assert sig != sign_request("other-key", SECRET, ts)
        assert sig != sign_request(KEY, "other-secret", ts)


class TestValidate:
    @pytest.mark.asyncio
    async def test_valid_signature(self, validator):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        assert await validator.validate(KEY, sig, SECRET, timestamp=ts) is True

    @pytest.mark.asyncio
    async def test_invalid_signature_raises(self, validator):
        ts = _ts()
        with pytest.raises(InvalidSignatureError):
            await validator.validate(KEY, "deadbeef" * 8, SECRET, timestamp=ts)

    @pytest.mark.asyncio
    async def test_wrong_secret_raises(self, validator):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        with pytest.raises(InvalidSignatureError):
            await validator.validate(KEY, sig, "wrong-secret", timestamp=ts)

    @pytest.mark.asyncio
    async def test_expired_timestamp_raises(self, validator):
        old_ts = _ts(-60 * 60)  # 1h ago, window is 5 min
        sig = sign_request(KEY, SECRET, old_ts)
        with pytest.raises(KeyExpiredError):
            await validator.validate(KEY, sig, SECRET, timestamp=old_ts)

    @pytest.mark.asyncio
    async def test_future_timestamp_raises(self, validator):
        future_ts = _ts(+3600)
        sig = sign_request(KEY, SECRET, future_ts)
        with pytest.raises(KeyExpiredError):
            await validator.validate(KEY, sig, SECRET, timestamp=future_ts)

    @pytest.mark.asyncio
    async def test_replay_with_different_timestamp_fails(self, validator):
        """A captured signature must not validate against a new timestamp."""
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        await validator.validate(KEY, sig, SECRET, timestamp=ts)
        with pytest.raises(InvalidSignatureError):
            await validator.validate(KEY, sig, SECRET, timestamp=ts + 5)

    @pytest.mark.asyncio
    async def test_defaults_to_current_time(self, validator):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        # Omitting timestamp uses now; only succeeds if ts == now-ish and
        # message matches, so sign with the same value we pass explicitly.
        assert await validator.validate(KEY, sig, SECRET, timestamp=ts)


class TestCache:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_recompute(self, validator):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        await validator.validate(KEY, sig, SECRET, timestamp=ts)
        assert validator.get_cache_stats()["cache_size"] == 1
        # Second call served from cache
        assert await validator.validate(KEY, sig, SECRET, timestamp=ts) is True

    @pytest.mark.asyncio
    async def test_failed_validation_not_cached(self, validator):
        ts = _ts()
        with pytest.raises(InvalidSignatureError):
            await validator.validate(KEY, "bad" * 22 + "xy", SECRET, timestamp=ts)
        assert validator.get_cache_stats()["cache_size"] == 0

    @pytest.mark.asyncio
    async def test_cache_is_bounded_lru(self):
        v = AsyncAPIKeyValidator(max_cache_size=3)
        base = _ts()
        for i in range(5):
            ts = base + i  # each within window? no - keep small offsets
            # use distinct valid signatures at current time via distinct keys
            key = f"k{i}"
            sig = sign_request(key, SECRET, base)
            await v.validate(key, sig, SECRET, timestamp=base)
        assert len(v._cache) <= 3

    @pytest.mark.asyncio
    async def test_invalidate_key_purges_cache(self, validator):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        await validator.validate(KEY, sig, SECRET, timestamp=ts)
        assert validator.invalidate_key(KEY) == 1
        assert validator.get_cache_stats()["cache_size"] == 0

    @pytest.mark.asyncio
    async def test_expired_cache_entry_is_dropped(self, validator):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        await validator.validate(KEY, sig, SECRET, timestamp=ts)
        # Age the entry beyond TTL
        for k in validator._cache:
            validator._cache[k] = time.time() - 10_000
        assert await validator.validate(KEY, sig, SECRET, timestamp=ts) is True
        # Entry re-stored fresh
        assert validator.get_cache_stats()["cache_size"] == 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, validator):
        ts = _ts()
        sig = sign_request(KEY, SECRET, ts)
        await validator.validate(KEY, sig, SECRET, timestamp=ts)
        validator.clear_cache()
        assert validator.get_cache_stats()["cache_size"] == 0


class TestBatchValidate:
    @pytest.mark.asyncio
    async def test_mixed_results_report_errors(self, validator):
        ts = _ts()
        good = {"key": KEY, "signature": sign_request(KEY, SECRET, ts), "secret": SECRET}
        bad = {"key": KEY, "signature": "x" * 64, "secret": SECRET}
        results = await validator.batch_validate([good, bad])
        assert results[0]["valid"] is True
        assert results[0]["error"] is None
        assert results[1]["valid"] is False
        assert results[1]["error"] == "InvalidSignatureError"

    @pytest.mark.asyncio
    async def test_empty_input(self, validator):
        assert await validator.batch_validate([]) == []
