"""通达信风格技术指标（移植自 ROX3.0 analysis/indicators.py，改为纯列表实现）。

包含：BARSLAST / COUNT / FILTER / ZIG / PEAK / TROUGH / PEAKBARS / TROUGHBARS。

⚠ 未来函数红线：ZIG/PEAK/TROUGH 的拐点只有在反向波动超过阈值后才确认，
即拐点位置随未来数据回补修正（look-ahead）。因此：
- 只能用于"历史结构标注"和复盘可视化；
- 严禁作为回测信号或实时买卖信号（回测会天然作弊）。
所有输出都必须携带此警示。
"""
from __future__ import annotations

FUTURE_FUNCTION_NOTE = "ZIG/PEAK 拐点含未来函数（事后确认），仅用于历史结构标注，不可作为实时或回测信号。"


def barslast(condition: list[bool]) -> list[int]:
    """距条件上次为真经过的 Bar 数；条件当根为 0，从未为真则从起点计数。"""
    result: list[int] = []
    since = 0
    seen = False
    for i, cond in enumerate(condition):
        if cond:
            since = 0
            seen = True
            result.append(0)
        else:
            since += 1
            result.append(since if seen else i)
    return result


def count(condition: list[bool], period: int) -> list[int]:
    """最近 period 根 Bar 内条件为真的次数。"""
    flags = [1 if c else 0 for c in condition]
    result: list[int] = []
    running = 0
    for i, flag in enumerate(flags):
        running += flag
        if i >= period:
            running -= flags[i - period]
        result.append(running)
    return result


def filter_(condition: list[bool], n: int) -> list[bool]:
    """信号后 n 根 Bar 内保持为真（FILTER，注意与通达信"过滤"语义差异，此处沿用前身实现）。"""
    out: list[bool] = []
    for i in range(len(condition)):
        out.append(any(condition[max(0, i - n + 1): i + 1]))
    return out


def find_pivots(closes: list[float], pct_change: float) -> list[int]:
    """ZIG 拐点检测：1=峰，-1=谷，0=普通点。

    pct_change 为百分比阈值（如 8 表示 8%）。最后一个拐点可能被未来数据推翻。
    """
    n = len(closes)
    pivots = [0] * n
    if n < 2 or pct_change <= 0:
        return pivots

    trend = 0
    last_pivot_price = closes[0]
    last_pivot_idx = 0
    for i in range(1, n):
        ret = closes[i] / last_pivot_price - 1.0
        if abs(ret) * 100 >= pct_change:
            pivots[last_pivot_idx] = -1 if ret > 0 else 1
            trend = 1 if ret > 0 else -1
            last_pivot_price = closes[i]
            last_pivot_idx = i
            break
    if trend == 0:
        return pivots

    extreme_price = last_pivot_price
    extreme_idx = last_pivot_idx
    for i in range(last_pivot_idx + 1, n):
        price = closes[i]
        if trend == 1:  # 上升趋势找峰
            if price >= extreme_price:
                extreme_price, extreme_idx = price, i
            elif (extreme_price - price) / extreme_price * 100 >= pct_change:
                pivots[extreme_idx] = 1
                trend = -1
                extreme_price, extreme_idx = price, i
        else:  # 下降趋势找谷
            if price <= extreme_price:
                extreme_price, extreme_idx = price, i
            elif (price - extreme_price) / extreme_price * 100 >= pct_change:
                pivots[extreme_idx] = -1
                trend = 1
                extreme_price, extreme_idx = price, i
    pivots[extreme_idx] = trend
    return pivots


def zig(closes: list[float], pct_change: float) -> list[float | None]:
    """ZIG 折线：拐点之间线性插值；其余点为插值结果。"""
    n = len(closes)
    if n == 0:
        return []
    pivots = find_pivots(closes, pct_change)
    known = [i for i in range(n) if pivots[i] != 0]
    if len(known) < 2:
        return [None] * n
    out: list[float | None] = [None] * n
    for a, b in zip(known, known[1:]):
        out[a] = closes[a]
        out[b] = closes[b]
        span = b - a
        for j in range(a + 1, b):
            out[j] = closes[a] + (closes[b] - closes[a]) * (j - a) / span
    return out


def peak_positions(closes: list[float], pct_change: float) -> list[int]:
    """确认峰的下标列表（含未来函数警示语义）。"""
    return [i for i, p in enumerate(find_pivots(closes, pct_change)) if p == 1]


def trough_positions(closes: list[float], pct_change: float) -> list[int]:
    """确认谷的下标列表。"""
    return [i for i, p in enumerate(find_pivots(closes, pct_change)) if p == -1]


def pivots_summary(closes: list[float], dates: list[str], pct_change: float) -> dict:
    """输出可序列化的拐点摘要（供复盘/研究卡使用），带未来函数警示。"""
    pivots = find_pivots(closes, pct_change)
    items = [
        {"index": i, "date": dates[i] if i < len(dates) else None,
         "type": "peak" if p == 1 else "trough", "price": closes[i]}
        for i, p in enumerate(pivots) if p != 0
    ]
    return {
        "threshold_pct": pct_change,
        "pivot_count": len(items),
        "pivots": items,
        "note": FUTURE_FUNCTION_NOTE,
    }
