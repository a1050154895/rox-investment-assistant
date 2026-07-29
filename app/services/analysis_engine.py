"""可复现的个股分析计算。

本模块只使用传入的行情、财务快照、资金流和K线，不生成随机指标。
数据缺失时返回不可用状态，由调用方明确展示。
"""
from __future__ import annotations

from typing import Any


def clamp(value: float, low: float = 0, high: float = 100) -> int:
    return round(max(low, min(high, value)))


def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))][-period:]
    gains = sum(max(delta, 0) for delta in deltas) / period
    losses = sum(max(-delta, 0) for delta in deltas) / period
    if losses == 0:
        return 100.0
    rs = gains / losses
    return round(100 - 100 / (1 + rs), 1)


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return result


def calculate_indicators(candles: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [float(candle["close"]) for candle in candles if candle.get("close") is not None]
    if len(closes) < 20:
        return {
            "data_status": "unavailable", "message": "有效K线不足20条，无法计算技术指标。",
            "rsi": None, "kdj_j": None, "macd": None, "macd_signal": None,
            "ma5": None, "ma20": None, "ma60": None, "boll_upper": None, "boll_lower": None,
        }
    ma = lambda period: round(sum(closes[-period:]) / period, 2) if len(closes) >= period else None
    ema12, ema26 = ema(closes, 12), ema(closes, 26)
    macd = round((ema12 or 0) - (ema26 or 0), 3) if ema12 is not None and ema26 is not None else None
    ma20_value = sum(closes[-20:]) / 20
    variance = sum((value - ma20_value) ** 2 for value in closes[-20:]) / 20
    deviation = variance ** 0.5
    return {
        "data_status": "calculated", "message": None,
        "rsi": calculate_rsi(closes), "kdj_j": None, "macd": macd, "macd_signal": None,
        "ma5": ma(5), "ma20": round(ma20_value, 2), "ma60": ma(60),
        "boll_upper": round(ma20_value + 2 * deviation, 2),
        "boll_lower": round(ma20_value - 2 * deviation, 2),
    }


def build_analysis(quote: dict[str, Any], fund_flow: dict[str, Any]) -> dict[str, Any]:
    price = float(quote.get("price") or 0)
    pe = float(quote.get("pe") or 0)
    pb = float(quote.get("pb") or 0)
    roe = round(pe / pb, 1) if pe > 0 and pb > 0 else None

    value_score = clamp(80 - max(pe - 15, 0) * 1.2 - max(pb - 3, 0) * 4) if pe and pb else None
    flow = fund_flow.get("main_inflow")
    flow_score = clamp(50 + float(flow) * 3) if flow is not None else None
    quality_score = clamp((roe or 0) * 3.2) if roe is not None else None
    discipline_score = 70

    available = [score for score in (value_score, flow_score, quality_score, discipline_score) if score is not None]
    total = round(sum(available) / len(available)) if len(available) >= 3 else None
    dimensions = {
        "value_law": {"score": value_score, "weight": 35, "label": "估值与价值", "detail": f"PE {pe:.1f} / PB {pb:.2f}" if pe and pb else "财务数据不足"},
        "fund_flow": {"score": flow_score, "weight": 25, "label": "资金流验证", "detail": f"主力净流入 {float(flow):+.2f} 亿" if flow is not None else "资金流数据不可用"},
        "quality": {"score": quality_score, "weight": 25, "label": "经营质量代理", "detail": f"PE/PB 推导ROE代理 {roe:.1f}%" if roe is not None else "ROE代理不可用"},
        "discipline": {"score": discipline_score, "weight": 15, "label": "纪律约束", "detail": "默认仅允许首仓观察，需更多独立信号确认"},
    }
    return {
        "consistency_score": total,
        "score_label": "数据不足" if total is None else ("高" if total >= 75 else "中等" if total >= 45 else "低"),
        "dimensions": dimensions,
        "value_assessment": {
            "current_price": price, "pe": pe or None, "pb": pb or None, "roe_proxy": roe,
            "value_grade": "需结合真实财报验证", "intrinsic_price": None,
            "deviation_ratio": None, "deviation_pct": None,
        },
        "analysis_status": "calculated" if total is not None else "insufficient_data",
        "method_version": "deterministic-v1",
        "position_recommendation": {
            "stage": "仅观察/首仓评估", "trigger": "至少2项独立真实信号验证",
            "rule": "数据缺失不得提升仓位；本结果不构成投资建议。",
        },
    }
