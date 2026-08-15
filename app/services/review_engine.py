"""每日股市复盘引擎。

聚合指数行情、板块涨跌、涨跌停统计、资金流向、市场情绪，
生成结构化每日复盘数据。所有数据来自腾讯公开行情接口，
不生成随机数据。
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from app.services.tencent_data import fetch_global_indices, fetch_kline, fetch_quotes
from app.services.market_data import REAL_QUOTES, REAL_INDICES

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 300  # 5 分钟

# 复盘用的指数代码（腾讯格式）
_INDEX_CODES = {
    "000001": "上证指数",
    "399001": "深证成指",
    "399006": "创业板指",
    "000300": "沪深300",
    "000016": "上证50",
    "399005": "中小板指",
}

# 复盘用的代表性个股池（覆盖主要行业）
_REVIEW_POOL = list(REAL_QUOTES.keys())


async def _fetch_index_data() -> list[dict[str, Any]]:
    """获取主要指数行情。"""
    codes = list(_INDEX_CODES.keys())
    quotes = await fetch_quotes(codes, is_index=True)
    indices = []
    for code in codes:
        name = _INDEX_CODES[code]
        q = quotes.get(code)
        if q and q.get("price", 0) > 0:
            indices.append({
                "name": name,
                "code": code,
                "price": round(q["price"], 2),
                "change_pct": round(q["change_pct"], 2),
                "change": round(q["change"], 2),
                "volume": q.get("volume", 0),
                "as_of": q.get("as_of", ""),
            })
        else:
            # 降级到快照
            for snap in REAL_INDICES:
                if snap["code"].startswith(code):
                    indices.append({**snap, "as_of": "快照"})
                    break
    return indices


async def _fetch_market_breadth() -> dict[str, Any]:
    """统计样本池涨跌情况（基于腾讯实时行情）。"""
    quotes = await fetch_quotes(_REVIEW_POOL)
    if not quotes:
        # 降级到快照
        quotes = REAL_QUOTES

    up_count = sum(1 for q in quotes.values() if q.get("change_pct", 0) > 0)
    down_count = sum(1 for q in quotes.values() if q.get("change_pct", 0) < 0)
    flat_count = sum(1 for q in quotes.values() if q.get("change_pct", 0) == 0)
    limit_up = sum(1 for q in quotes.values() if q.get("change_pct", 0) >= 9.9)
    limit_down = sum(1 for q in quotes.values() if q.get("change_pct", 0) <= -9.9)

    # 涨幅前5和跌幅前5
    sorted_by_pct = sorted(quotes.items(), key=lambda x: x[1].get("change_pct", 0), reverse=True)
    top_gainers = [
        {"code": code, "name": q.get("name", ""), "change_pct": round(q.get("change_pct", 0), 2)}
        for code, q in sorted_by_pct[:5] if q.get("change_pct", 0) > 0
    ]
    top_losers = [
        {"code": code, "name": q.get("name", ""), "change_pct": round(q.get("change_pct", 0), 2)}
        for code, q in sorted_by_pct[-5:] if q.get("change_pct", 0) < 0
    ]

    total = len(quotes)
    return {
        "total_stocks": total,
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": flat_count,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "up_ratio": round(up_count / total * 100, 1) if total else 0,
        "down_ratio": round(down_count / total * 100, 1) if total else 0,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
    }


async def _fetch_sector_performance() -> list[dict[str, Any]]:
    """获取板块资金流向（复用 intelligence_data 的 AKShare 接口）。"""
    try:
        import akshare as ak
        frame = await asyncio.wait_for(
            asyncio.to_thread(ak.stock_sector_fund_flow_rank, "5", "行业"),
            timeout=8
        )
        if frame is None or frame.empty:
            raise ValueError("空数据")
        sectors = []
        for _, row in frame.head(10).iterrows():
            sectors.append({
                "sector": str(row.get("名称", "")),
                "flow": float(row.get("主力净流入-净额", 0) or 0),
                "flow_pct": float(row.get("主力净流入-净占比", 0) or 0),
                "trend": "inflow" if float(row.get("主力净流入-净额", 0) or 0) > 0 else "outflow",
            })
        return sectors
    except Exception as exc:
        logger.info("板块资金流获取失败，使用快照: %s", exc)
        from app.services.intelligence_data import SECTOR_FLOW
        return SECTOR_FLOW


def _calc_sentiment(indices: list[dict], breadth: dict) -> dict[str, Any]:
    """计算市场情绪综合评分（0-100）。"""
    score = 50  # 基准

    # 指数涨跌贡献
    for idx in indices:
        pct = idx.get("change_pct", 0)
        if pct > 1:
            score += 5
        elif pct > 0:
            score += 2
        elif pct < -1:
            score -= 5
        elif pct < 0:
            score -= 2

    # 涨跌比贡献
    up_ratio = breadth.get("up_ratio", 50)
    if up_ratio > 70:
        score += 10
    elif up_ratio > 55:
        score += 5
    elif up_ratio < 30:
        score -= 10
    elif up_ratio < 45:
        score -= 5

    # 涨跌停贡献
    limit_up = breadth.get("limit_up", 0)
    limit_down = breadth.get("limit_down", 0)
    if limit_up > 3:
        score += 5
    if limit_down > 3:
        score -= 5

    score = max(0, min(100, score))
    if score >= 75:
        label = "强势"
        suggestion = "市场情绪高涨，可关注领涨板块龙头，但注意追高风险"
    elif score >= 60:
        label = "偏强"
        suggestion = "市场有一定赚钱效应，适合结构化操作，控制仓位"
    elif score >= 40:
        label = "中性"
        suggestion = "市场分化，宜观望或轻仓试探，等待方向明确"
    elif score >= 25:
        label = "偏弱"
        suggestion = "市场承压，建议降低仓位，关注防御性板块"
    else:
        label = "弱势"
        suggestion = "市场情绪低迷，建议观望为主，不宜盲目抄底"

    return {"score": score, "label": label, "suggestion": suggestion}


def _generate_review_summary(indices: list[dict], breadth: dict, sentiment: dict, sectors: list[dict]) -> str:
    """生成结构化复盘摘要（非AI，基于数据规则）。"""
    today = datetime.now().strftime("%Y年%m月%d日")
    parts = [f"【{today} 市场复盘】"]

    # 指数表现
    idx_parts = []
    for idx in indices[:4]:
        direction = "涨" if idx["change_pct"] > 0 else "跌"
        idx_parts.append(f"{idx['name']}{direction}{abs(idx['change_pct']):.2f}%")
    parts.append("指数表现：" + "，".join(idx_parts) + "。")

    # 涨跌家数
    parts.append(
        f"样本池中 {breadth['up_count']} 涨 / {breadth['down_count']} 跌 / "
        f"{breadth['flat_count']} 平，涨停 {breadth['limit_up']} 家，跌停 {breadth['limit_down']} 家。"
    )

    # 情绪
    parts.append(f"市场情绪：{sentiment['label']}（{sentiment['score']}分）。{sentiment['suggestion']}")

    # 板块
    inflow_sectors = [s for s in sectors if s.get("trend") == "inflow"][:3]
    outflow_sectors = [s for s in sectors if s.get("trend") == "outflow"][:3]
    if inflow_sectors:
        parts.append("资金流入前列：" + "、".join(s["sector"] for s in inflow_sectors) + "。")
    if outflow_sectors:
        parts.append("资金流出前列：" + "、".join(s["sector"] for s in outflow_sectors) + "。")

    # 领涨领跌
    if breadth.get("top_gainers"):
        top = breadth["top_gainers"][0]
        parts.append(f"样本领涨：{top['name']}({top['change_pct']:+.2f}%)。")
    if breadth.get("top_losers"):
        bottom = breadth["top_losers"][-1]
        parts.append(f"样本领跌：{bottom['name']}({bottom['change_pct']:+.2f}%)。")

    parts.append("以上为公开行情数据的结构化复盘，非投资建议。")
    return "".join(parts)


async def get_daily_review(force: bool = False) -> dict[str, Any]:
    """获取每日复盘数据。"""
    cache_key = "daily_review"
    cached = _CACHE.get(cache_key)
    if cached and not force and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    try:
        indices, breadth, sectors, global_idx = await asyncio.gather(
            _fetch_index_data(),
            _fetch_market_breadth(),
            _fetch_sector_performance(),
            fetch_global_indices(),
        )
    except Exception as exc:
        logger.error("复盘数据获取失败: %s", exc)
        indices, breadth, sectors, global_idx = [], {"total_stocks": 0, "up_count": 0, "down_count": 0}, [], []

    sentiment = _calc_sentiment(indices, breadth)
    summary = _generate_review_summary(indices, breadth, sentiment, sectors)

    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "indices": indices,
        "breadth": breadth,
        "sectors": sectors,
        "global_indices": global_idx,
        "sentiment": sentiment,
        "summary": summary,
        "data_source": "腾讯公开行情 + AKShare 板块资金流",
        "disclaimer": "本复盘为公开行情数据的结构化整理，非投资建议。",
    }

    _CACHE[cache_key] = (time.time(), result)
    return result


async def get_review_history(days: int = 7) -> list[dict[str, Any]]:
    """获取历史复盘摘要（基于K线数据生成简化版）。"""
    history = []
    try:
        # 用上证指数K线生成近N个交易日的简化复盘
        klines = await fetch_kline("000001", "day", days + 5, is_index=True)
        if klines:
            recent = klines[-days:]
            for k in recent:
                date = k["date"]
                close = k["close"]
                open_price = k["open"]
                change_pct = round((close - open_price) / open_price * 100, 2) if open_price else 0
                if change_pct > 1:
                    sentiment_label = "偏强"
                elif change_pct > -1:
                    sentiment_label = "中性"
                else:
                    sentiment_label = "偏弱"
                history.append({
                    "date": date,
                    "index_price": round(close, 2),
                    "change_pct": change_pct,
                    "sentiment": sentiment_label,
                    "volume": k.get("volume", 0),
                })
    except Exception as exc:
        logger.warning("历史复盘获取失败: %s", exc)

    return history


# ============ 资本周期阶段判定 ============

CAPITAL_CYCLE_STAGES = ["积累", "集中", "流转", "分配", "再生产"]

_CYCLE_DETAIL = {
    "积累": "涨跌互现、情绪中性，资金缓慢蓄积，等待方向明确。",
    "集中": "资金向少数主线集中，局部出现赚钱效应。",
    "流转": "普涨、广度全面，资金在行业间轮动。",
    "分配": "指数高位但广度回落，资金流出领涨板块，警惕顶部。",
    "再生产": "普跌、情绪低迷、资金流出，市场重新洗牌。",
}

_CYCLE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CYCLE_CACHE_TTL = 300


def classify_capital_cycle(
    up_ratio: float,
    score: int,
    limit_up: int,
    limit_down: int,
    inflow: int,
    outflow: int,
    index_avg: float,
) -> str:
    """纯函数：根据市场广度、情绪、资金流与指数动量判定资本周期阶段。"""
    if up_ratio >= 60:
        return "流转"
    if up_ratio <= 35:
        return "再生产"
    if index_avg > 0 and up_ratio < 55 and outflow > inflow and limit_down > 0:
        return "分配"
    if inflow >= 2 and inflow > outflow and limit_up > 0 and up_ratio >= 45:
        return "集中"
    return "积累"


def _cycle_confidence(up_ratio: float, score: int, inflow: int, outflow: int) -> str:
    strong = 0
    if up_ratio >= 60 or up_ratio <= 40:
        strong += 1
    if score >= 60 or score <= 40:
        strong += 1
    if abs(inflow - outflow) >= 3:
        strong += 1
    return "高" if strong >= 2 else ("中" if strong == 1 else "低")


async def get_capital_cycle_stage(force: bool = False) -> dict[str, Any]:
    """资本周期阶段判定：基于可观测信号，数据不足时诚实返回「未评估」。"""
    cache_key = "cycle_stage"
    cached = _CYCLE_CACHE.get(cache_key)
    if cached and not force and time.time() - cached[0] < _CYCLE_CACHE_TTL:
        return cached[1]

    indices = await _fetch_index_data()
    breadth = await _fetch_market_breadth()
    sectors = await _fetch_sector_performance()

    total = breadth.get("total_stocks", 0)
    if total == 0:
        result = {
            "stages": CAPITAL_CYCLE_STAGES,
            "current_stage": None,
            "stage_name": "未评估",
            "progress": 0,
            "stage_detail": "缺少可靠的成交结构、资金流和宏观数据，暂不判断周期阶段",
            "evidence": "",
            "confidence": None,
            "signals": {},
            "rule": "不先定阶段，不要讲仓位；阶段判断不清时建议观望",
        }
        _CYCLE_CACHE[cache_key] = (time.time(), result)
        return result

    sentiment = _calc_sentiment(indices, breadth)
    up_ratio = breadth.get("up_ratio", 0)
    limit_up = breadth.get("limit_up", 0)
    limit_down = breadth.get("limit_down", 0)
    score = sentiment.get("score", 50)
    inflow = sum(1 for s in sectors if s.get("trend") == "inflow")
    outflow = sum(1 for s in sectors if s.get("trend") == "outflow")
    index_avg = round(sum(i.get("change_pct", 0) for i in indices) / len(indices), 2) if indices else 0.0

    stage = classify_capital_cycle(up_ratio, score, limit_up, limit_down, inflow, outflow, index_avg)
    result = {
        "stages": CAPITAL_CYCLE_STAGES,
        "current_stage": CAPITAL_CYCLE_STAGES.index(stage),
        "stage_name": stage,
        "progress": round((CAPITAL_CYCLE_STAGES.index(stage) + 1) / len(CAPITAL_CYCLE_STAGES) * 100),
        "stage_detail": _CYCLE_DETAIL[stage],
        "evidence": f"上涨占比 {up_ratio}% · 情绪 {sentiment['label']}({score}分) · 流入板块 {inflow} / 流出 {outflow}",
        "confidence": _cycle_confidence(up_ratio, score, inflow, outflow),
        "signals": {
            "up_ratio": up_ratio,
            "down_ratio": breadth.get("down_ratio", 0),
            "limit_up": limit_up,
            "limit_down": limit_down,
            "sentiment_score": score,
            "sentiment_label": sentiment.get("label"),
            "inflow_sectors": inflow,
            "outflow_sectors": outflow,
            "index_avg_change": index_avg,
        },
        "rule": "广度+情绪+资金流综合判定，经验规则，仅作参考，不构成投资建议。",
    }
    _CYCLE_CACHE[cache_key] = (time.time(), result)
    return result
