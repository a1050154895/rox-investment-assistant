"""个股基本面研究引擎。

数据来源：
- AKShare stock_financial_abstract_ths（同花顺财务摘要，近5年年报）
- AKShare stock_financial_analysis_indicator（财务指标，86列）
- 腾讯行情（实时 PE/PB/市值）

所有数字标注来源，缺失标 [MISSING]，不编造。
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from app.services.tencent_data import fetch_quotes

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 600  # 10 分钟


def _parse_cn(v) -> float | None:
    """解析中文数字：'1.47亿'→1.47e8, '23.38%'→23.38, 'False'→None"""
    if v is None or v is False:
        return None
    s = str(v).strip()
    if s in ("False", "None", "--", "", "nan", "NaN"):
        return None
    s = s.rstrip("%")
    try:
        return float(s)
    except ValueError:
        pass
    try:
        if s.endswith("亿"):
            return float(s[:-1]) * 1e8
        if s.endswith("万"):
            return float(s[:-1]) * 1e4
        if s.endswith("万亿"):
            return float(s[:-2]) * 1e12
    except (ValueError, IndexError):
        pass
    return None


def _fmt_yi(val: float | None) -> str:
    """格式化为'亿元'"""
    if val is None:
        return "[MISSING]"
    return f"{val / 1e8:.2f}亿"


async def _fetch_financial_summary(code: str) -> list[dict[str, Any]]:
    """获取近5年年报财务摘要。"""
    try:
        import akshare as ak
        df = await asyncio.wait_for(
            asyncio.to_thread(ak.stock_financial_abstract_ths, symbol=code),
            timeout=15
        )
        if df is None or df.empty:
            return []

        df["报告期"] = df["报告期"].astype(str)
        annual = df[df["报告期"].str.endswith("12-31")].head(5).iloc[::-1]

        rows = []
        for _, r in annual.iterrows():
            rows.append({
                "period": str(r["报告期"]),
                "revenue": _parse_cn(r.get("营业总收入")),
                "revenue_yoy": _parse_cn(r.get("营业总收入同比增长率")),
                "net_profit": _parse_cn(r.get("净利润")),
                "net_profit_yoy": _parse_cn(r.get("净利润同比增长率")),
                "eps": _parse_cn(r.get("基本每股收益")),
                "bps": _parse_cn(r.get("每股净资产")),
                "gross_margin": _parse_cn(r.get("销售毛利率")),
                "net_margin": _parse_cn(r.get("销售净利率")),
                "roe": _parse_cn(r.get("净资产收益率")),
                "debt_ratio": _parse_cn(r.get("资产负债率")),
                "current_ratio": _parse_cn(r.get("流动比率")),
                "quick_ratio": _parse_cn(r.get("速动比率")),
            })
        return rows
    except Exception as exc:
        logger.warning("财务摘要获取失败 %s: %s", code, exc)
        return []


async def _fetch_valuation(code: str) -> dict[str, Any]:
    """获取实时估值数据（腾讯行情）。"""
    try:
        quotes = await fetch_quotes([code])
        q = quotes.get(code)
        if not q:
            return {"status": "unavailable"}

        return {
            "status": "realtime",
            "price": round(q["price"], 2),
            "pe_ttm": round(q["pe"], 2) if q.get("pe", 0) > 0 else None,
            "pb": round(q["pb"], 2) if q.get("pb", 0) > 0 else None,
            "market_cap": round(q["market_cap"], 2) if q.get("market_cap", 0) > 0 else None,
            "as_of": q.get("as_of", ""),
            "name": q.get("name", ""),
        }
    except Exception as exc:
        logger.warning("估值获取失败 %s: %s", code, exc)
        return {"status": "unavailable"}


def _calc_quality_score(summary: list[dict]) -> dict[str, Any]:
    """财务质量评分（杜邦分解思路，0-100）。"""
    if len(summary) < 2:
        return {"score": None, "label": "数据不足", "details": {}}

    latest = summary[-1]
    prev = summary[-2]

    scores = {}

    # 盈利能力（ROE）
    roe = latest.get("roe")
    if roe is not None:
        if roe >= 20:
            scores["盈利能力"] = 25
        elif roe >= 15:
            scores["盈利能力"] = 20
        elif roe >= 10:
            scores["盈利能力"] = 15
        elif roe >= 5:
            scores["盈利能力"] = 10
        else:
            scores["盈利能力"] = 5
    else:
        scores["盈利能力"] = None

    # 成长性（营收增速）
    rev_yoy = latest.get("revenue_yoy")
    if rev_yoy is not None:
        if rev_yoy >= 20:
            scores["成长性"] = 25
        elif rev_yoy >= 10:
            scores["成长性"] = 20
        elif rev_yoy >= 0:
            scores["成长性"] = 10
        else:
            scores["成长性"] = 0
    else:
        scores["成长性"] = None

    # 财务安全（资产负债率，越低越好）
    debt = latest.get("debt_ratio")
    if debt is not None:
        if debt <= 30:
            scores["财务安全"] = 25
        elif debt <= 50:
            scores["财务安全"] = 20
        elif debt <= 65:
            scores["财务安全"] = 12
        else:
            scores["财务安全"] = 5
    else:
        scores["财务安全"] = None

    # 营运效率（毛利率，行业差异大但作粗筛）
    gm = latest.get("gross_margin")
    if gm is not None:
        if gm >= 50:
            scores["营运效率"] = 20
        elif gm >= 30:
            scores["营运效率"] = 15
        elif gm >= 15:
            scores["营运效率"] = 10
        else:
            scores["营运效率"] = 5
    else:
        scores["营运效率"] = None

    # 稳定性（ROE 是否持续）
    roe_history = [r.get("roe") for r in summary if r.get("roe") is not None]
    if len(roe_history) >= 3:
        roe_std = (sum((x - sum(roe_history) / len(roe_history)) ** 2 for x in roe_history) / len(roe_history)) ** 0.5
        if roe_std < 3:
            scores["稳定性"] = 5
        elif roe_std < 8:
            scores["稳定性"] = 3
        else:
            scores["稳定性"] = 1
    else:
        scores["稳定性"] = None

    valid = [v for v in scores.values() if v is not None]
    total = sum(valid) if valid else 0
    max_possible = sum(25 if k != "营运效率" and k != "稳定性" else (20 if k == "营运效率" else 5) for k, v in scores.items() if v is not None)
    normalized = round(total / max_possible * 100, 1) if max_possible > 0 else 0

    if normalized >= 80:
        label = "优秀"
    elif normalized >= 65:
        label = "良好"
    elif normalized >= 50:
        label = "中等"
    elif normalized >= 35:
        label = "偏弱"
    else:
        label = "风险"

    return {"score": normalized, "label": label, "details": scores}


def _generate_investment_notes(summary: list[dict], valuation: dict, quality: dict) -> str:
    """生成基本面投资要点（基于数据规则，非AI）。"""
    if not summary:
        return "财务数据暂不可用，无法生成基本面分析。"
    latest = summary[-1]
    parts = []

    # 盈利
    roe = latest.get("roe")
    if roe is not None:
        if roe >= 20:
            parts.append(f"ROE {roe:.1f}%，盈利能力强，资本回报率优异。")
        elif roe >= 15:
            parts.append(f"ROE {roe:.1f}%，盈利能力良好。")
        elif roe >= 10:
            parts.append(f"ROE {roe:.1f}%，盈利能力中等。")
        else:
            parts.append(f"ROE {roe:.1f}%，盈利能力偏弱，需关注回报率改善。")

    # 成长
    rev_yoy = latest.get("revenue_yoy")
    np_yoy = latest.get("net_profit_yoy")
    if rev_yoy is not None and np_yoy is not None:
        if rev_yoy > 0 and np_yoy > rev_yoy:
            parts.append(f"营收增长 {rev_yoy:.1f}%，净利润增长 {np_yoy:.1f}%，利润增速快于营收，经营杠杆正向释放。")
        elif rev_yoy > 0:
            parts.append(f"营收增长 {rev_yoy:.1f}%，净利润增长 {np_yoy:.1f}%。")
        elif rev_yoy < 0:
            parts.append(f"营收下滑 {abs(rev_yoy):.1f}%，需关注增长瓶颈。")

    # 财务安全
    debt = latest.get("debt_ratio")
    if debt is not None:
        if debt > 70:
            parts.append(f"资产负债率 {debt:.1f}%，杠杆偏高，需关注偿债风险。")
        elif debt < 30:
            parts.append(f"资产负债率 {debt:.1f}%，财务结构稳健。")

    # 估值
    pe = valuation.get("pe_ttm")
    pb = valuation.get("pb")
    if pe is not None:
        if pe > 50:
            parts.append(f"PE(TTM) {pe:.1f}倍，估值偏高，市场定价隐含高增长预期。")
        elif pe < 10:
            parts.append(f"PE(TTM) {pe:.1f}倍，估值偏低，需结合行业判断是否价值陷阱。")
        else:
            parts.append(f"PE(TTM) {pe:.1f}倍。")
    if pb is not None and pb > 5:
        parts.append(f"PB {pb:.1f}倍，净资产溢价较高。")

    # 质量
    if quality.get("score") is not None:
        parts.append(f"财务质量评分 {quality['score']:.0f}分（{quality['label']}）。")

    parts.append("以上为公开财务数据的结构化分析，非投资建议。")
    return "".join(parts)


async def get_fundamentals(code: str, force: bool = False) -> dict[str, Any]:
    """获取个股基本面全貌。"""
    cache_key = f"fund_{code}"
    cached = _CACHE.get(cache_key)
    if cached and not force and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    try:
        summary, valuation = await asyncio.gather(
            _fetch_financial_summary(code),
            _fetch_valuation(code),
        )
    except Exception as exc:
        logger.error("基本面获取失败 %s: %s", code, exc)
        summary, valuation = [], {"status": "unavailable"}

    quality = _calc_quality_score(summary)
    notes = _generate_investment_notes(summary, valuation, quality)

    result = {
        "code": code,
        "name": valuation.get("name", ""),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "valuation": valuation,
        "quality": quality,
        "notes": notes,
        "data_source": "AKShare 财务摘要 + 腾讯实时行情",
        "disclaimer": "本数据为公开财务信息的结构化整理，非投资建议。",
    }

    _CACHE[cache_key] = (time.time(), result)
    return result
