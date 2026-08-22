"""AKShare 调用限流门（吸收自 ROX3.0 akshare_wrapper 的限流思想）。

AKShare 公开接口对高频访问敏感，全局限流 + 简单重试可以显著降低
被限流/超时的概率。纯 async 实现，不做线程级抢锁（to_thread 之前 acquire）。
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable


class RateGate:
    """最小间隔限流：两次调用之间至少间隔 min_interval 秒。"""

    def __init__(self, min_interval: float = 0.25, clock: Callable[[], float] = time.monotonic):
        self.min_interval = min_interval
        self._clock = clock
        self._last = float("-inf")
        self._lock = asyncio.Lock()

    def _wait_seconds(self) -> float:
        now = self._clock()
        elapsed = now - self._last
        if elapsed >= self.min_interval:
            self._last = now
            return 0.0
        wait = self.min_interval - elapsed
        self._last = now + wait
        return wait

    async def acquire(self) -> float:
        """获取调用权；返回实际等待的秒数（0 表示未等待）。"""
        async with self._lock:
            wait = self._wait_seconds()
        if wait > 0:
            await asyncio.sleep(wait)
        return wait


_GATE = RateGate()


async def gated_call(
    fn: Callable[[], Any],
    gate: RateGate | None = None,
    retries: int = 1,
    retry_delay: float = 0.8,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> Any:
    """带限流与重试的同步函数调用（放进 to_thread 由调用方或本函数处理）。

    fn 应为阻塞函数；本函数负责限流间隔与一次重试。
    """
    gate = gate or _GATE
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        await gate.acquire()
        try:
            return await asyncio.to_thread(fn)
        except Exception as exc:  # noqa: BLE001 — 重试后仍失败则上抛
            last_error = exc
            if attempt < retries:
                await sleep(retry_delay)
    raise last_error  # type: ignore[misc]
