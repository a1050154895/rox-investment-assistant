"""基金/ETF 研究数据适配层。

只承载可核验的基金元数据；实时价格与K线复用市场数据服务，
无法取得净值、持仓或跟踪误差时明确返回不可用，不生成替代值。
"""
from typing import Any

from app.services.market_data import get_kline, get_stock_quote


ETF_METADATA: dict[str, dict[str, Any]] = {
    "510300": {"name": "沪深300ETF", "fund_type": "ETF", "tracking": "沪深300", "category": "宽基"},
    "510500": {"name": "中证500ETF", "fund_type": "ETF", "tracking": "中证500", "category": "宽基"},
    "159915": {"name": "创业板ETF", "fund_type": "ETF", "tracking": "创业板指", "category": "宽基"},
    "512100": {"name": "中证1000ETF", "fund_type": "ETF", "tracking": "中证1000", "category": "宽基"},
    "512880": {"name": "证券ETF", "fund_type": "ETF", "tracking": "证券公司", "category": "行业"},
    "512690": {"name": "酒ETF", "fund_type": "ETF", "tracking": "中证酒", "category": "行业"},
    "512480": {"name": "半导体ETF", "fund_type": "ETF", "tracking": "半导体", "category": "行业"},
    "515790": {"name": "光伏ETF", "fund_type": "ETF", "tracking": "光伏产业", "category": "行业"},
}


def search_funds(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = query.strip().lower()
    return [
        {"code": code, **meta}
        for code, meta in ETF_METADATA.items()
        if not q or q in code or q in meta["name"].lower() or q in meta["tracking"].lower()
    ][:limit]


async def get_fund(code: str) -> dict[str, Any]:
    normalized = code.strip().lower().replace(".sh", "").replace(".sz", "")
    metadata = ETF_METADATA.get(normalized)
    if not metadata:
        return {"error": "暂不支持该基金代码，当前先支持常用ETF研究。", "data_status": "unavailable"}
    quote = await get_stock_quote(normalized)
    return {
        "code": normalized,
        **metadata,
        "quote": quote,
        "data_status": quote.get("data_status", "unavailable"),
        "data_source": quote.get("data_source"),
        "as_of": quote.get("as_of"),
        "stale": quote.get("stale", True),
        "disclosures": {
            "nav": {"status": "unavailable", "message": "基金净值接口尚未接入，不用行情价格冒充净值。"},
            "holdings": {"status": "unavailable", "message": "持仓披露接口尚未接入，需以基金定期报告为准。"},
            "tracking_error": {"status": "unavailable", "message": "跟踪误差需要净值与指数序列后计算。"},
        },
    }


async def get_fund_kline(code: str, period: str = "daily") -> dict[str, Any]:
    if code.strip().lower().replace(".sh", "").replace(".sz", "") not in ETF_METADATA:
        return {"candles": [], "data_status": "unavailable", "message": "暂不支持该基金代码"}
    return await get_kline(code, period)
