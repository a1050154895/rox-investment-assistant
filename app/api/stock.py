"""个股透视 API — K线数据、框架分析、资金流向

数据源：腾讯自选股公开接口（行情/K线/搜索，本地与 Render 均可用）→ AKShare → NeoData 快照
方法论：卢麒元五层逻辑链 + 框架一致性评分体系
"""
from fastapi import APIRouter, Query

from app.services.analysis_engine import build_analysis, calculate_indicators
from app.services.data_contract import ensure_contract
from app.services.tdx_indicators import FUTURE_FUNCTION_NOTE, pivots_summary
from app.services.market_data import (
    get_stock_quote, get_kline, get_fund_flow, REAL_QUOTES,
)
from app.services.tencent_data import smartbox_search

router = APIRouter()


@router.get("/search")
async def search_stocks(q: str = Query("", max_length=20, description="搜索关键词：代码或名称")):
    """搜索股票 — 腾讯自选股实时全市场搜索（A股，含代码/名称/拼音）；不可用时降级内置池。"""
    query = q.strip()
    if not query:
        return {"results": [], "coverage": "smartbox", "message": "请输入代码或名称"}

    results = await smartbox_search(query, limit=10)
    # 兼容 sh600519 / sz000001 前缀写法：剥离前缀后重查
    if not results and len(query) > 2 and query[:2].lower() in ("sh", "sz", "bj"):
        results = await smartbox_search(query[2:], limit=10)
    if results:
        for r in results:
            r["industry"] = REAL_QUOTES.get(r["code"], {}).get("industry", "")
        return {"results": results, "coverage": "smartbox"}

    # 降级：内置池
    ql = query.lower()
    fallback = []
    for code, info in REAL_QUOTES.items():
        if ql in code or ql in info["name"].lower() or ql in info.get("industry", "").lower():
            fallback.append({"code": code, "name": info["name"], "industry": info.get("industry", "")})
    return {"results": fallback[:10], "coverage": "builtin"}


@router.get("/{code}")
async def stock_info(code: str):
    """个股实时行情（统一数据状态契约出口）"""
    return ensure_contract(await get_stock_quote(code))


@router.get("/{code}/kline")
async def kline(code: str, period: str = Query("daily", description="周期: daily/weekly")):
    """K线数据 — AKShare 实时获取，失败时回退到真实价格快照"""
    return ensure_contract(await get_kline(code, period))


@router.get("/{code}/pivots")
async def stock_pivots(code: str, threshold: float = Query(8.0, ge=1.0, le=30.0, description="拐点阈值百分比")):
    """ZIG 关键转折点（峰/谷）——仅用于历史结构标注与复盘。

    含未来函数：拐点在反向波动超阈值后才确认，禁止作为实时/回测信号。
    """
    kline = await get_kline(code, "daily", 250)
    candles = kline.get("candles", [])
    if len(candles) < 10:
        return {"error": "K线数据不足，无法计算拐点", "pivots": [], "note": FUTURE_FUNCTION_NOTE}
    closes = [c["close"] for c in candles]
    dates = [str(c.get("date", "")) for c in candles]
    summary = pivots_summary(closes, dates, threshold)
    return {
        "code": code,
        **summary,
        "candle_count": len(candles),
        "data_status": kline.get("data_status"),
        "data_source": kline.get("data_source"),
        "as_of": dates[-1] if dates else None,
    }


@router.get("/{code}/analysis")
async def stock_analysis(code: str):
    """个股框架分析 — 基于五维度一致性评分体系

    评分权重：矛盾分析30% + 价值规律35% + 宏观周期25% + 技术分析5% + 纪律5%
    """
    quote = await get_stock_quote(code)
    if "error" in quote:
        return quote

    name = quote.get("name", code)
    fund_flow = await get_fund_flow(code)
    analysis = build_analysis(quote, fund_flow)

    from app.services.intelligence_data import get_stock_intelligence
    intelligence = await get_stock_intelligence(code, name, quote.get("industry", ""))

    return {
        "code": code, "name": name, **analysis,
        "contradictions": {
            "primary": {"name": "待真实数据验证", "intensity": None, "desc": "不使用随机矛盾强度"},
            "secondary": {"name": "待真实数据验证", "intensity": None},
            "all_types": [],
        },
        "fund_flow": fund_flow, "intelligence": intelligence,
        "data_status": quote.get("data_status"), "data_source": quote.get("data_source"),
        "as_of": quote.get("as_of"), "stale": quote.get("stale", False),
    }


@router.get("/{code}/indicators")
async def indicators(code: str):
    """基于真实K线确定性计算技术指标。"""
    kline_data = await get_kline(code, "daily", limit=120)
    result = calculate_indicators(kline_data.get("candles", []))
    return {
        "code": code, **result,
        "source_status": kline_data.get("data_status"),
        "data_source": kline_data.get("data_source"),
        "stale": kline_data.get("stale", True),
    }
