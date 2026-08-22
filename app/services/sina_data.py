"""新浪财经 K 线直连（吸收自 ROX3.0 ashare_fallback 的新浪日线接口）。

作为 K 线降级链的一环：腾讯 → AKShare → 新浪直连 → 历史快照。
公开接口、无鉴权；失败返回 None，由调用方继续降级，不生成模拟数据。
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
# scale = 分钟数：日线 240，周线 1200
_SCALES = {"daily": 240, "weekly": 1200}
TIMEOUT_SECONDS = 8.0


def _sina_symbol(code: str) -> str:
    code = str(code).strip().lower()
    for prefix in ("sh", "sz", "bj"):
        if code.startswith(prefix):
            code = code[2:]
            break
    code = code.split(".")[0].zfill(6)
    if code.startswith(("6", "5", "9")):
        return f"sh{code}"
    return f"sz{code}"


def _parse_rows(text: str) -> list[dict[str, Any]]:
    rows = json.loads(text)
    candles = []
    for row in rows:
        try:
            candles.append({
                "date": str(row.get("day", ""))[:10],
                "open": float(row.get("open", 0)),
                "close": float(row.get("close", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "volume": int(float(row.get("volume", 0) or 0)),
            })
        except (TypeError, ValueError):
            continue
    return candles


async def fetch_sina_kline(code: str, period: str = "daily", limit: int = 120) -> list[dict[str, Any]] | None:
    """新浪K线；不可用时返回 None（调用方继续降级）。"""
    scale = _SCALES.get(period, 240)
    params = {"symbol": _sina_symbol(code), "scale": scale, "ma": "no", "datalen": str(min(limit, 1023))}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.get(_BASE, params=params, headers={"Referer": "https://finance.sina.com.cn"})
            resp.raise_for_status()
            candles = _parse_rows(resp.text)
            return candles[-limit:] if candles else None
    except Exception as exc:  # noqa: BLE001 — 降级链的一环，失败静默交给下一环
        logger.info("新浪K线不可用 code=%s error=%s", code, exc)
        return None
