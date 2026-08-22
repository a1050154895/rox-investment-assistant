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
        "evidence_coverage": {
            "market_price": {"status": quote.get("data_status", "unavailable"), "source": quote.get("data_source"), "as_of": quote.get("as_of"), "message": "场内交易价格"},
            "kline": {"status": quote.get("data_status", "unavailable"), "source": quote.get("data_source"), "as_of": quote.get("as_of"), "message": "可用于交易价格风险观察"},
            "nav": {"status": "unavailable", "source": None, "as_of": None, "message": "基金净值接口尚未接入"},
            "iopv": {"status": "unavailable", "source": None, "as_of": None, "message": "IOPV/盘中参考净值接口尚未接入"},
            "premium_discount": {"status": "unavailable", "source": None, "as_of": None, "message": "缺少净值或IOPV，不能计算折溢价"},
            "holdings": {"status": "unavailable", "source": None, "as_of": None, "message": "持仓披露接口尚未接入，需以基金定期报告为准"},
            "tracking_error": {"status": "unavailable", "source": None, "as_of": None, "message": "需要净值与指数序列后计算"},
        },
    }


async def get_fund_kline(code: str, period: str = "daily") -> dict[str, Any]:
    if code.strip().lower().replace(".sh", "").replace(".sz", "") not in ETF_METADATA:
        return {"candles": [], "data_status": "unavailable", "message": "暂不支持该基金代码"}
    result = await get_kline(code, period)
    candles = result.get("candles", [])
    if candles:
        closes = [float(item["close"]) for item in candles if item.get("close") is not None]
        if len(closes) >= 2:
            peak = closes[0]
            max_drawdown = 0.0
            for close in closes:
                peak = max(peak, close)
                max_drawdown = min(max_drawdown, (close / peak - 1) * 100)
            daily_returns = [(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes)) if closes[i - 1]]
            mean_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
            variance = sum((value - mean_return) ** 2 for value in daily_returns) / len(daily_returns) if daily_returns else 0.0
            result["metrics"] = {
                "sample_count": len(closes),
                "period_return_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "volatility_proxy_pct": round(variance ** 0.5, 2),
                "as_of": candles[-1].get("date"),
                "note": "基于交易价格K线，不代表基金净值收益或跟踪误差。",
            }
    return result
