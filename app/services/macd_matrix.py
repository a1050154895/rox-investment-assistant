"""多周期 MACD 状态矩阵。

用同一套 MACD(12,26,9) 在 日/周/月/季 多个周期上分别描述趋势状态：
- 日/周/月 K 线来自腾讯前复权接口（真实数据）；
- 季K 由月线按日历季度聚合（确定性重采样，不引入外部数据）；
- 年K 需要 ≥35 根年度样本，数据源历史长度不足，如实返回 unavailable。

边界（与技术指标红线一致）：
- 只输出历史状态描述（DIF/DEA 相对位置、最近一次交叉的时间），
  不输出买卖信号、不做预测；状态是否可用由用户结合基本面交叉判断。
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date

from app.services.tencent_data import fetch_kline

FAST, SLOW, SIGNAL = 12, 26, 9
_MIN_BARS = 35  # EMA26 + DEA9 稳定所需的最少样本
_PERIODS = ("yearly", "quarterly", "monthly", "weekly", "daily")
_PERIOD_LABELS = {"yearly": "年", "quarterly": "季", "monthly": "月", "weekly": "周", "daily": "日"}
_STATE_LABELS = {"golden": "金叉（DIF 在 DEA 上方）", "death": "死叉（DIF 在 DEA 下方）"}


def ema(values: list[float], period: int) -> list[float]:
    """标准 EMA 递推：首值作种子，k = 2/(period+1)。确定性。"""
    k = 2 / (period + 1)
    out: list[float] = []
    prev: float | None = None
    for v in values:
        prev = v if prev is None else prev + k * (v - prev)
        out.append(prev)
    return out


def macd_series(closes: list[float]) -> list[dict]:
    """返回逐 bar 的 {dif, dea, hist}；样本不足时前面元素为 None。"""
    if len(closes) < SLOW:
        return [{"dif": None, "dea": None, "hist": None} for _ in closes]
    ema_fast = ema(closes, FAST)
    ema_slow = ema(closes, SLOW)
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea = ema(dif, SIGNAL)
    return [
        {"dif": round(d, 4), "dea": round(e, 4), "hist": round(d - e, 4)}
        for d, e in zip(dif, dea)
    ]


def _quarter_key(day_str: str) -> str:
    d = date.fromisoformat(day_str[:10])
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def aggregate_monthly_to_quarters(bars: list[dict]) -> list[dict]:
    """月线 → 季线：按日历季度聚合 OHLCV（开=首日开，收=末日收，高/低=极值，量=求和）。"""
    quarters: OrderedDict[str, dict] = OrderedDict()
    for bar in bars:
        key = _quarter_key(str(bar.get("date", "")))
        q = quarters.get(key)
        if q is None:
            quarters[key] = {
                "date": key, "open": bar.get("open"), "close": bar.get("close"),
                "high": bar.get("high"), "low": bar.get("low"), "volume": bar.get("volume") or 0,
            }
        else:
            q["close"] = bar.get("close")
            q["high"] = max(q.get("high") or 0, bar.get("high") or 0)
            q["low"] = min(q.get("low") or 0, bar.get("low") or 0) if bar.get("low") is not None else q.get("low")
            q["volume"] = (q.get("volume") or 0) + (bar.get("volume") or 0)
    return list(quarters.values())


def _last_cross(dif: list, dea: list) -> dict | None:
    """最近一次 DIF 与 DEA 的相对位置翻转。"""
    for i in range(len(dif) - 1, 0, -1):
        if dif[i] is None or dea[i] is None or dif[i - 1] is None or dea[i - 1] is None:
            return None
        prev_above = dif[i - 1] > dea[i - 1]
        now_above = dif[i] > dea[i]
        if prev_above != now_above:
            return {"type": "golden" if now_above else "death", "bars_ago": len(dif) - 1 - i}
    return None


def _period_state(bars: list[dict], label: str, source: str) -> dict:
    base = {"period": label}
    closes = [float(b.get("close")) for b in bars if b.get("close") is not None]
    dates = [str(b.get("date", "")) for b in bars if b.get("close") is not None]
    if len(closes) < _MIN_BARS:
        return {
            **base, "data_status": "unavailable", "bars": len(closes),
            "message": f"样本不足（{len(closes)} < {_MIN_BARS} 根），拒绝计算",
        }
    series = macd_series(closes)
    last = series[-1]
    as_of = dates[-1] if dates else ""
    result = {
        **base,
        "data_status": "realtime",
        "bars": len(closes),
        "as_of": as_of,
        "dif": last["dif"],
        "dea": last["dea"],
        "hist": last["hist"],
        "state": "golden" if last["dif"] > last["dea"] else "death",
        "state_label": _STATE_LABELS["golden" if last["dif"] > last["dea"] else "death"],
        "last_cross": _last_cross([s["dif"] for s in series], [s["dea"] for s in series]),
        "data_source": source,
    }
    return result


async def macd_matrix(code: str) -> dict:
    """多周期 MACD 状态矩阵；每个周期独立标注数据状态，缺失即缺失。"""
    day_bars = await fetch_kline(code, period="day", limit=250)
    week_bars = await fetch_kline(code, period="week", limit=160)
    month_bars = await fetch_kline(code, period="month", limit=140)

    periods: list[dict] = []
    if month_bars:
        periods.append(_period_state(aggregate_monthly_to_quarters(month_bars), "quarterly", "腾讯月线按季度聚合"))
    else:
        periods.append({"period": "quarterly", "data_status": "unavailable", "message": "月线数据不可用，无法聚合季线"})
    if month_bars:
        periods.append(_period_state(month_bars, "monthly", "腾讯前复权月线"))
    else:
        periods.append({"period": "monthly", "data_status": "unavailable", "message": "月线数据不可用"})
    if week_bars:
        periods.append(_period_state(week_bars, "weekly", "腾讯前复权周线"))
    else:
        periods.append({"period": "weekly", "data_status": "unavailable", "message": "周线数据不可用"})
    if day_bars:
        periods.append(_period_state(day_bars, "daily", "腾讯前复权日线"))
    else:
        periods.append({"period": "daily", "data_status": "unavailable", "message": "日线数据不可用"})
    periods.append({
        "period": "yearly", "data_status": "unavailable",
        "message": "年线级 MACD 需 ≥35 年历史，数据源不提供，如实不计算",
    })
    periods.sort(key=lambda p: _PERIODS.index(p["period"]))

    available = [p for p in periods if p.get("data_status") == "realtime"]
    overall = "partial" if available and len(available) < len(periods) else ("realtime" if available else "unavailable")
    return {
        "code": code,
        "data_status": overall,
        "data_source": "腾讯自选股公开接口（前复权 K 线），季线由月线按日历季度聚合",
        "as_of": max((p.get("as_of") or "" for p in available), default=""),
        "periods": periods,
        "note": "本矩阵只描述历史指标状态，不构成买卖信号；状态是否可用请与基本面、纪律检查交叉验证。",
    }
