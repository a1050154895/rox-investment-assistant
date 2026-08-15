"""网络调用的重试与熔断，用于数据源短暂抖动时提升可用性。"""
import asyncio
import time


class CircuitBreaker:
    """连续失败达到阈值后打开熔断，冷却期内快速失败，冷却结束后自动放行探测。"""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._consecutive_failures = 0
        self._opened_at = 0.0

    @property
    def is_open(self) -> bool:
        if self._consecutive_failures < self.failure_threshold:
            return False
        if time.monotonic() - self._opened_at >= self.cooldown_seconds:
            self._consecutive_failures = 0
            return False
        return True

    def record_success(self) -> None:
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._opened_at = time.monotonic()


class CircuitOpenError(RuntimeError):
    """熔断器打开，跳过本次网络调用。"""


async def run_with_retry(
    coro_factory,
    *,
    retries: int = 1,
    base_delay: float = 0.5,
    breaker: CircuitBreaker | None = None,
    retry_on: tuple[type[Exception], ...] | None = None,
):
    """对异步调用做带退避的重试，可选熔断器。

    coro_factory 每次调用返回一个新的 awaitable；retry_on 为空时对所有异常重试，
    否则仅对指定异常类型重试（用于跳过超时这类重试无益的情况）。
    """
    for attempt in range(retries + 1):
        if breaker is not None and breaker.is_open:
            raise CircuitOpenError("circuit open")
        try:
            result = await coro_factory()
        except Exception as exc:
            if breaker is not None:
                breaker.record_failure()
            retryable = retry_on is None or isinstance(exc, retry_on)
            if attempt < retries and retryable:
                await asyncio.sleep(base_delay * (2 ** attempt))
                continue
            raise
        if breaker is not None:
            breaker.record_success()
        return result
