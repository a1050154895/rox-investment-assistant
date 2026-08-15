"""重试与熔断的离线单元测试。"""
import asyncio
import time

import pytest

from app.services.resilience import CircuitBreaker, CircuitOpenError, run_with_retry


def test_retry_then_succeed():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ConnectionError("transient")
        return "ok"

    assert asyncio.run(run_with_retry(flaky, retry_on=(ConnectionError,))) == "ok"
    assert calls["n"] == 2


def test_retry_exhausted_raises():
    calls = {"n": 0}

    async def always_fail():
        calls["n"] += 1
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        asyncio.run(run_with_retry(always_fail, retries=2, base_delay=0, retry_on=(ConnectionError,)))
    assert calls["n"] == 3


def test_no_retry_on_non_retryable():
    calls = {"n": 0}

    async def timeout():
        calls["n"] += 1
        raise TimeoutError("hang")

    with pytest.raises(TimeoutError):
        asyncio.run(run_with_retry(timeout, retries=2, base_delay=0, retry_on=(ConnectionError,)))
    assert calls["n"] == 1


def test_breaker_opens_and_fails_fast():
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=30)
    calls = {"n": 0}

    async def fail():
        calls["n"] += 1
        raise ConnectionError("down")

    for _ in range(2):
        with pytest.raises(ConnectionError):
            asyncio.run(run_with_retry(fail, retries=0, breaker=breaker))
    assert breaker.is_open is True

    with pytest.raises(CircuitOpenError):
        asyncio.run(run_with_retry(fail, retries=0, breaker=breaker))
    assert calls["n"] == 2  # 熔断打开后不再真正调用


def test_breaker_closes_after_cooldown():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30)

    async def fail():
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        asyncio.run(run_with_retry(fail, retries=0, breaker=breaker))
    assert breaker.is_open is True

    breaker._opened_at = time.monotonic() - 31
    assert breaker.is_open is False
