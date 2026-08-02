"""个股透视 API — K线数据、框架分析、资金流向

数据源：AKShare 实时数据（Render 部署时生效）+ NeoData 真实数据快照（本地兜底）
方法论：卢麒元五层逻辑链 + 框架一致性评分体系
"""
from fastapi import APIRouter, Query

from app.services.analysis_engine import build_analysis, calculate_indicators
from app.services.market_data import (
    get_stock_quote, get_kline, get_fund_flow, load_stock_universe, REAL_QUOTES,
)

router = APIRouter()


@router.get("/search")
async def search_stocks(q: str = Query("", max_length=20, description="搜索关键词：代码或名称")):
    """搜索股票 — 覆盖沪深京全市场 A 股（AKShare 名录 + 本地缓存）；数据源不可用时降级内置池。"""
    query = q.strip().lower()
    if not query:
        return {"results": [], "coverage": "a-share", "message": "请输入代码或名称"}

    universe = load_stock_universe()
    results: list[dict] = []
    seen: set[str] = set()

    # 兼容 sh600519 / sz000001 前缀写法
    bare = query
    for prefix in ("sh", "sz", "bj"):
        if bare.startswith(prefix):
            bare = bare[2:]
            break

    def _match(code: str, name: str) -> bool:
        if bare and bare in code:
            return True
        if query and query in code:
            return True
        return bool(query and query in name.lower())

    for item in universe:
        code, name = item["code"], item["name"]
        if not _match(code, name) or code in seen:
            continue
        seen.add(code)
        results.append({"code": code, "name": name, "industry": REAL_QUOTES.get(code, {}).get("industry", "")})
        if len(results) >= 10:
            break

    # 降级：名录不可用时回退内置池
    if not results:
        for code, info in REAL_QUOTES.items():
            if query in code or query in info["name"].lower() or query in info.get("industry", "").lower():
                results.append({"code": code, "name": info["name"], "industry": info.get("industry", "")})

    return {
        "results": results[:10],
        "coverage": "a-share" if universe else "builtin",
        "total_universe": len(universe),
    }


@router.get("/{code}")
async def stock_info(code: str):
    """个股实时行情"""
    return await get_stock_quote(code)


@router.get("/{code}/kline")
async def kline(code: str, period: str = Query("daily", description="周期: daily/weekly")):
    """K线数据 — AKShare 实时获取，失败时回退到真实价格快照"""
    return await get_kline(code, period)


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
