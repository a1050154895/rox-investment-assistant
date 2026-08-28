"""基金/ETF 研究数据适配层。

只承载可核验的基金元数据；实时价格与K线复用市场数据服务，
无法取得净值、持仓或跟踪误差时明确返回不可用，不生成替代值。
跟踪误差目前提供「价格口径代理」（ETF 场内价 vs 跟踪指数收盘），
明确标注与净值口径的差异，不冒充正式跟踪误差。
"""
import math
from typing import Any

from app.services.market_data import get_kline, get_stock_quote
from app.services.tencent_data import fetch_kline
from app.services.tencent_data import smartbox_search


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

# ETF → 跟踪指数六位代码（腾讯指数K线可取）；无法取得指数K线的保持不可用
TRACKING_INDEX: dict[str, str] = {
    "510300": "000300",
    "510500": "000905",
    "159915": "399006",
    "512100": "000852",
    "512880": "399975",
    "512690": "399987",
    "515790": "931151",
}


def compute_tracking_proxy(
    etf_candles: list[dict[str, Any]],
    index_candles: list[dict[str, Any]],
    min_days: int = 20,
) -> dict[str, Any] | None:
    """价格口径跟踪误差代理：ETF 场内价日收益 vs 指数收盘日收益。

    口径说明：不含费用、分红与申赎影响，不等于基金净值跟踪误差；
    样本不足时返回 None（调用方保持不可用，不造数）。
    """
    index_by_date = {
        str(c.get("date")): c.get("close") for c in index_candles if c.get("close")
    }
    pairs = [
        (float(c["close"]), float(index_by_date[c["date"]]))
        for c in etf_candles
        if c.get("close") and str(c.get("date")) in index_by_date
    ]
    if len(pairs) < min_days + 1:
        return None
    etf_returns = [pairs[i][0] / pairs[i - 1][0] - 1 for i in range(1, len(pairs)) if pairs[i - 1][0]]
    idx_returns = [pairs[i][1] / pairs[i - 1][1] - 1 for i in range(1, len(pairs)) if pairs[i - 1][1]]
    if len(etf_returns) != len(idx_returns) or not etf_returns:
        return None
    diffs = [e - i for e, i in zip(etf_returns, idx_returns)]
    mean_diff = sum(diffs) / len(diffs)
    variance = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
    tracking_error = math.sqrt(variance) * math.sqrt(244) * 100
    # 日收益相关系数
    mean_e = sum(etf_returns) / len(etf_returns)
    mean_i = sum(idx_returns) / len(idx_returns)
    cov = sum((e - mean_e) * (i - mean_i) for e, i in zip(etf_returns, idx_returns))
    var_e = sum((e - mean_e) ** 2 for e in etf_returns)
    var_i = sum((i - mean_i) ** 2 for i in idx_returns)
    correlation = cov / math.sqrt(var_e * var_i) if var_e > 0 and var_i > 0 else None
    return {
        "tracking_error_annualized_pct": round(tracking_error, 2),
        "daily_diff_mean_pct": round(mean_diff * 100, 4),
        "correlation": round(correlation, 4) if correlation is not None else None,
        "sample_days": len(diffs),
        "basis": "价格口径代理（场内价 vs 指数收盘，不含费用与分红）",
    }


async def _tracking_error_entry(code: str) -> dict[str, Any]:
    index_code = TRACKING_INDEX.get(code)
    if not index_code:
        return {
            "status": "unavailable", "source": None, "as_of": None,
            "message": "跟踪指数K线暂不可取，净值口径跟踪误差待数据源接入",
        }
    try:
        etf = await get_kline(code, "daily", limit=250)
        index_candles = await fetch_kline(index_code, "day", 250, is_index=True)
        proxy = compute_tracking_proxy(etf.get("candles", []), index_candles or [])
    except Exception:
        proxy = None
    if not proxy:
        return {
            "status": "unavailable", "source": "腾讯指数K线 × ETF价格K线", "as_of": None,
            "message": "指数与ETF价格样本不足或接口不可用，暂不计算",
        }
    as_of = (etf.get("candles") or [{}])[-1].get("date")
    return {
        "status": "snapshot",
        "source": "腾讯指数K线 × ETF价格K线",
        "as_of": as_of,
        "message": (
            f"年化跟踪误差代理 {proxy['tracking_error_annualized_pct']}% · "
            f"相关性 {proxy['correlation']} · {proxy['sample_days']} 个交易日"
        ),
        "proxy": proxy,
    }


async def search_funds(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """搜索基金：先查内置 ETF 元数据，再从腾讯全市场搜索补全 LOF/ETF。"""
    q = query.strip().lower()
    metadata_results = [
        {"code": code, **meta}
        for code, meta in ETF_METADATA.items()
        if not q or q in code or q in meta["name"].lower() or q in meta["tracking"].lower()
    ]
    results = metadata_results[:limit]
    if len(results) >= limit:
        return results

    smart = await smartbox_search(query, limit=limit * 2)
    seen_codes = {item["code"] for item in results}
    for item in smart:
        code = item.get("code", "")
        if code and code not in seen_codes:
            results.append({"code": code, "name": item.get("name", ""), "tracking": "待核验", "fund_type": "场内基金", "category": ""})
            seen_codes.add(code)
            if len(results) >= limit:
                break
    return results


async def get_fund(code: str) -> dict[str, Any]:
    normalized = code.strip().lower().replace(".sh", "").replace(".sz", "")
    metadata = ETF_METADATA.get(normalized)
    if not metadata:
        metadata = {"name": "场内基金", "fund_type": "场内基金", "tracking": "待核验", "category": ""}
    quote = await get_stock_quote(normalized)
    if quote.get("data_status") == "unavailable":
        return {"error": "场内基金行情暂不可用，请稍后重试或改用代码搜索。", "data_status": "unavailable"}
    tracking = await _tracking_error_entry(normalized)
    return {
        "code": normalized,
        **metadata,
        "name": quote.get("name") or metadata["name"],
        "quote": quote,
        "data_status": quote.get("data_status", "unavailable"),
        "data_source": quote.get("data_source"),
        "as_of": quote.get("as_of"),
        "stale": quote.get("stale", True),
        "evidence_coverage": {
            "market_price": {"status": quote.get("data_status", "unavailable"), "source": quote.get("data_source"), "as_of": quote.get("as_of"), "message": "场内交易价格"},  # noqa: E501
            "kline": {"status": quote.get("data_status", "unavailable"), "source": quote.get("data_source"), "as_of": quote.get("as_of"), "message": "可用于交易价格风险观察"},  # noqa: E501
            "nav": {"status": "unavailable", "source": None, "as_of": None, "message": "基金净值接口尚未接入"},
            "iopv": {"status": "unavailable", "source": None, "as_of": None, "message": "IOPV/盘中参考净值接口尚未接入"},
            "premium_discount": {"status": "unavailable", "source": None, "as_of": None, "message": "缺少净值或IOPV，不能计算折溢价"},  # noqa: E501
            "holdings": {"status": "unavailable", "source": None, "as_of": None, "message": "持仓披露接口尚未接入，需以基金定期报告为准"},  # noqa: E501
            "tracking_error": tracking,
        },
    }


async def get_fund_kline(code: str, period: str = "daily") -> dict[str, Any]:
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
            variance = (
                sum((value - mean_return) ** 2 for value in daily_returns) / len(daily_returns)
                if daily_returns else 0.0
            )
            result["metrics"] = {
                "sample_count": len(closes),
                "period_return_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "volatility_proxy_pct": round(variance ** 0.5, 2),
                "as_of": candles[-1].get("date"),
                "note": "基于交易价格K线，不代表基金净值收益或跟踪误差。",
            }
    return result
