"""矛盾分析引擎 — 识别量价 / 资金 / 结构 / 预期四类核心矛盾。

方法论：卢麒元矛盾分析法。四类矛盾对应框架 L3 的 contradiction_types：
量价矛盾、资金矛盾、结构矛盾、预期矛盾。
数据来源：指数量价、市场广度、板块资金流、宏观矩阵（财政信用 × 价值实现）。
矛盾强度 0-100，>70 为强矛盾；数据不足时诚实降级，绝不编造矛盾。
"""
import logging
import time
from typing import Any

from app.services.macro_data import get_macro_matrix
from app.services.review_engine import _fetch_index_data, _fetch_market_breadth, _fetch_sector_performance

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 300


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def analyze_contradictions(
    index_avg: float,
    up_ratio: float,
    inflow: int,
    outflow: int,
    credit_score: float | None,
    real_score: float | None,
) -> list[dict[str, Any]]:
    """纯函数：根据市场与宏观信号计算四类矛盾的强度、趋势与证据。"""
    results: list[dict[str, Any]] = []

    # 1) 量价矛盾：指数方向 vs 赚钱效应（上涨占比）背离
    index_score = _clamp(50 + index_avg * 10)
    vp_gap = abs(up_ratio - index_score)
    if index_avg > 0.5 and up_ratio < 45:
        vp_trend = "指数强、个股弱"
    elif index_avg < -0.5 and up_ratio > 55:
        vp_trend = "指数弱、个股强"
    else:
        vp_trend = "量价一致"
    results.append({
        "key": "volume_price",
        "name": "量价矛盾",
        "type": "量能 vs 赚钱效应",
        "intensity": round(_clamp(vp_gap * 1.5), 1),
        "trend": vp_trend,
        "desc": f"指数平均 {index_avg:+.2f}%，上涨占比 {up_ratio}%，背离度 {vp_gap:.1f}。",
        "evidence": f"指数 {index_avg:+.2f}% · 上涨占比 {up_ratio}%",
    })

    # 2) 资金矛盾：板块流入/流出分歧（以板块资金流代理内外资分歧）
    total_flow = inflow + outflow
    capital_intensity = _clamp(min(inflow, outflow) / total_flow * 200) if total_flow > 0 else 0.0
    if inflow and outflow:
        capital_trend = "流入流出并存"
    elif inflow > outflow:
        capital_trend = "整体净流入"
    elif outflow > inflow:
        capital_trend = "整体净流出"
    else:
        capital_trend = "无显著资金流"
    results.append({
        "key": "capital",
        "name": "资金矛盾",
        "type": "外资 vs 内资（板块资金分歧代理）",
        "intensity": round(capital_intensity, 1),
        "trend": capital_trend,
        "desc": f"资金流入板块 {inflow} 个、流出 {outflow} 个，分歧度 {capital_intensity:.1f}。",
        "evidence": f"流入板块 {inflow} / 流出 {outflow}",
    })

    # 3) 结构矛盾：行业分化 vs 指数共振（上涨占比越接近 50% 分化越明显）
    structure_intensity = _clamp(100 - abs(up_ratio - 50) * 2)
    results.append({
        "key": "structure",
        "name": "结构矛盾",
        "type": "行业分化 vs 指数共振",
        "intensity": round(structure_intensity, 1),
        "trend": "结构分化" if structure_intensity >= 60 else "指数共振",
        "desc": f"上涨占比 {up_ratio}%，越接近 50% 分化越明显，结构矛盾越强。",
        "evidence": f"上涨占比 {up_ratio}%",
    })

    # 4) 预期矛盾：政策/信用端 vs 实体经济端背离
    if credit_score is not None and real_score is not None:
        expectation_gap = abs(credit_score - real_score)
        if credit_score > real_score + 15:
            expectation_trend = "信用强、实体弱"
        elif real_score > credit_score + 15:
            expectation_trend = "实体强、信用弱"
        else:
            expectation_trend = "信用与实体一致"
        expectation_desc = f"信用端 {credit_score:.0f} 分 vs 实体端 {real_score:.0f} 分，背离 {expectation_gap:.1f} 分。"
        expectation_evidence = f"信用端 {credit_score:.0f} / 实体端 {real_score:.0f}"
    else:
        expectation_gap = 0.0
        expectation_trend = "数据不足"
        expectation_desc = "宏观数据不足，无法判断预期矛盾。"
        expectation_evidence = ""
    results.append({
        "key": "expectation",
        "name": "预期矛盾",
        "type": "政策预期 vs 经济现实",
        "intensity": round(_clamp(expectation_gap * 1.5), 1),
        "trend": expectation_trend,
        "desc": expectation_desc,
        "evidence": expectation_evidence,
    })

    return results


def _pick(contradictions: list[dict[str, Any]], rank: int) -> dict[str, Any]:
    ordered = sorted(contradictions, key=lambda c: c["intensity"], reverse=True)
    if rank >= len(ordered) or ordered[rank]["intensity"] <= 0:
        return {"name": "暂无", "type": "未评估", "intensity": 0, "trend": "unknown", "desc": "数据不足", "evidence": ""}
    c = ordered[rank]
    return {
        "key": c["key"],
        "name": c["name"],
        "type": c["type"],
        "intensity": c["intensity"],
        "trend": c["trend"],
        "desc": c["desc"],
        "evidence": c["evidence"],
    }


async def get_contradictions(force: bool = False) -> dict[str, Any]:
    """获取四类矛盾的强度排序，选出主要/次要/第三矛盾。"""
    cache_key = "contradictions"
    cached = _CACHE.get(cache_key)
    if cached and not force and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    indices = await _fetch_index_data()
    breadth = await _fetch_market_breadth()
    sectors = await _fetch_sector_performance()
    macro = await get_macro_matrix()

    if breadth.get("total_stocks", 0) == 0:
        empty = {"name": "待真实数据验证", "type": "未评估", "intensity": 0, "trend": "unknown", "desc": "不使用模拟强度", "evidence": ""}
        result = {
            "primary": empty,
            "secondary": empty,
            "tertiary": empty,
            "all": [],
            "rule": "只有经过来源校验的数据才能进入矛盾强度计算",
            "data_status": "degraded",
        }
        _CACHE[cache_key] = (time.time(), result)
        return result

    index_avg = round(sum(i.get("change_pct", 0) for i in indices) / len(indices), 2) if indices else 0.0
    up_ratio = breadth.get("up_ratio", 50)
    inflow = sum(1 for s in sectors if s.get("trend") == "inflow")
    outflow = sum(1 for s in sectors if s.get("trend") == "outflow")

    credit_score = macro.get("sovereign_credit", {}).get("score")
    real_score = macro.get("value_realization", {}).get("score")
    if not credit_score or not real_score:
        credit_score = real_score = None

    all_contradictions = analyze_contradictions(index_avg, up_ratio, inflow, outflow, credit_score, real_score)
    result = {
        "primary": _pick(all_contradictions, 0),
        "secondary": _pick(all_contradictions, 1),
        "tertiary": _pick(all_contradictions, 2),
        "all": all_contradictions,
        "rule": "矛盾强度>70为强矛盾，需重点关注；矛盾转化时调整持仓结构。",
        "data_status": "available" if (credit_score is not None and real_score is not None) else "degraded",
    }
    _CACHE[cache_key] = (time.time(), result)
    return result
