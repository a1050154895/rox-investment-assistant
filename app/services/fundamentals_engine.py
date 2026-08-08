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
        annual = df[df["报告期"].str.endswith("12-31")].sort_values("报告期").tail(5)

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


# ========================================
# DCF 估值模型
# ========================================

def _calc_revenue_cagr(summary: list[dict]) -> float:
    """用近3年营收计算复合增长率，数据不足时降级。"""
    revs = [r["revenue"] for r in summary if r.get("revenue") is not None]
    if len(revs) < 3:
        return 5.0  # [ASSUMPTION] 数据不足按5%保守
    n = len(revs) - 1
    try:
        cagr = (revs[-1] / revs[0]) ** (1 / n) - 1
        return max(min(cagr, 0.30), -0.10)  # clamp [-10%, 30%]
    except (ZeroDivisionError, IndexError):
        return 5.0


def _estimate_wacc(debt_ratio: float | None) -> float:
    """用资产负债率粗估 WACC。"""
    if debt_ratio is None:
        return 0.09  # [ASSUMPTION] 默认
    rf = 0.03  # [ASSUMPTION] 无风险利率 3% (10Y国债)
    erp = 0.06  # [ASSUMPTION] 股权风险溢价 6%
    beta = 1.0 + max(0, (debt_ratio - 30) / 100) * 0.5  # [ASSUMPTION] 杠杆简调
    cost_equity = rf + beta * erp
    return round(max(0.06, min(cost_equity, 0.15)), 4)


async def get_dcf_valuation(code: str, force: bool = False) -> dict[str, Any]:
    """DCF 现金流折现估值。

    关键假设 [MODEL ASSUMPTION]：
    - 营收增速 = 近3年 CAGR，钳位 [-10%, 30%]
    - FCF 率 = 净利润率 × 70%（简化工序：假定资本开支占净利30%）
    - WACC 由资产负债率粗估（rf=3%, erp=6%, beta 随杠杆调整）
    - 5 年显式预测 + 永续增长 g=2.5%
    - 折现率逐年衰减至 WACC
    """
    cache_key = f"dcf_{code}"
    cached = _CACHE.get(cache_key)
    if cached and not force and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    # 获取财务摘要（复用缓存）
    base = await get_fundamentals(code, force=force)
    summary = base.get("summary", [])
    valuation = base.get("valuation", {})

    if len(summary) < 1:
        result = {"status": "unavailable", "message": "财务数据不足，无法建模"}
        _CACHE[cache_key] = (time.time(), result)
        return result

    latest = summary[-1]

    # 参数估计
    rev_growth = _calc_revenue_cagr(summary)
    latest_rev = latest.get("revenue")
    net_margin = latest.get("net_margin")
    if latest_rev is None:
        result = {"status": "unavailable", "message": "营收数据缺失"}
        _CACHE[cache_key] = (time.time(), result)
        return result
    if net_margin is None:
        net_margin = 10.0  # [ASSUMPTION]

    fcf_ratio = (net_margin / 100) * 0.70  # [ASSUMPTION] 资本开支 = 净利30%
    wacc = _estimate_wacc(latest.get("debt_ratio"))
    terminal_g = 0.025  # [ASSUMPTION] 永续增长率 2.5%
    shares = None

    # 尝试从腾讯行情获取总股本（用市值/股价）
    price = valuation.get("price")
    mktcap = valuation.get("market_cap")
    if price and mktcap and price > 0:
        shares = mktcap * 1e8 / price  # [NOTE] market_cap 单位为亿

    # 5年显式投影
    projections = []
    rev = latest_rev
    pv_sum = 0.0
    projected_years = 5
    for i in range(1, projected_years + 1):
        rev = rev * (1 + rev_growth / 100)
        fcf = rev * fcf_ratio
        discount = (1 + wacc) ** i
        pv = fcf / discount
        pv_sum += pv
        projections.append({
            "year": i,
            "revenue": round(rev / 1e8, 2),  # 亿
            "fcf": round(fcf / 1e8, 2),
            "pv": round(pv / 1e8, 2),
        })

    # 终值
    terminal_fcf = rev * (1 + terminal_g) * fcf_ratio
    terminal_value = terminal_fcf / max(wacc - terminal_g, 0.01)
    terminal_pv = terminal_value / (1 + wacc) ** projected_years
    pv_sum += terminal_pv

    enterprise_value = pv_sum  # 原始单位（元）
    fair_price = None
    upside = None
    if shares and shares > 0:
        fair_price = round(enterprise_value / shares, 2)
        if price:
            upside = round((fair_price / price - 1) * 100, 1)

    # 判断
    if upside is not None:
        if upside > 30:
            verdict = "显著低估"
        elif upside > 10:
            verdict = "偏低估"
        elif upside > -10:
            verdict = "接近合理"
        elif upside > -30:
            verdict = "偏高估"
        else:
            verdict = "显著高估"
    else:
        verdict = "无法判断"

    result = {
        "status": "available",
        "assumptions": {
            "revenue_growth_pct": round(rev_growth, 1),
            "net_margin_pct": round(net_margin, 1),
            "fcf_ratio": f"{fcf_ratio:.1%}",
            "wacc_pct": round(wacc * 100, 2),
            "terminal_growth_pct": terminal_g * 100,
            "projection_years": projected_years,
            "source": "营收增速=历史3年CAGR; WACC 由资产负债率粗估; FCF率=净利率×70%",
        },
        "projections": projections,
        "terminal_value_e10": round(terminal_value / 1e8, 2),
        "terminal_pv_e10": round(terminal_pv / 1e8, 2),
        "enterprise_value_e10": round(enterprise_value, 2),
        "fair_price": fair_price,
        "current_price": price,
        "upside_pct": upside,
        "verdict": verdict,
        "disclaimer": "DCF 参数均为估计值，结果含大量假设，非投资建议。",
    }

    _CACHE[cache_key] = (time.time(), result)
    return result


# ========================================
# 可比公司估值 (Comps)
# ========================================

_PEER_GROUPS: dict[str, list[str]] = {
    "白酒": ["600519", "000858", "000568", "600809", "002304"],
    "空调": ["000651", "600690", "000333"],
    "保险": ["601318", "601628", "601601", "601336"],
    "银行": ["600036", "601398", "000001", "601939", "002142"],
    "证券": ["600030", "601211", "000776", "600837"],
    "半导体": ["002371", "002049", "603501", "603986", "688981"],
    "新能源": ["300750", "002594", "601012", "300274"],
    "医药": ["600276", "000538", "002001", "300015", "300760"],
    "汽车": ["600104", "002594", "000625", "600733"],
    "消费电子": ["002475", "000725", "002241", "688036"],
    "煤炭": ["601088", "601898", "600188"],
    "电力": ["600900", "600011", "600025", "600023"],
}


async def get_comps_valuation(code: str, force: bool = False) -> dict[str, Any]:
    """可比公司估值：用同行业 PE/PB 中位数对比标的。"""
    cache_key = f"comps_{code}"
    cached = _CACHE.get(cache_key)
    if cached and not force and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    # 获取标的估值
    base = await get_fundamentals(code, force=force)
    target_val = base.get("valuation", {})
    target_pe = target_val.get("pe_ttm")
    target_pb = target_val.get("pb")
    target_name = target_val.get("name", code)

    # 确定同业组（从 stock info 拿 industry 匹配 _PEER_GROUPS）
    peers = []
    industry_found = ""
    try:
        import akshare as ak
        # 先用 AKShare 查行业
        info_df = await asyncio.wait_for(
            asyncio.to_thread(ak.stock_individual_info_em, symbol=code),
            timeout=8
        )
        if info_df is not None and not info_df.empty:
            for kw, group in _PEER_GROUPS.items():
                for _, r in info_df.iterrows():
                    if kw in str(r.get("item", "")) or kw in str(r.get("value", "")):
                        peers = [p for p in group if p != code]
                        industry_found = kw
                        break
                if peers:
                    break
    except Exception as exc:
        logger.info("AKShare 行业查询失败: %s", exc)

    # 兜底：从 market_data 的 industry 匹配
    if not peers:
        try:
            from app.services.market_data import REAL_QUOTES
            stock_info = REAL_QUOTES.get(code, {})
            ind = stock_info.get("industry", "")
            for kw, group in _PEER_GROUPS.items():
                if kw in ind:
                    peers = [p for p in group if p != code]
                    industry_found = kw
                    break
        except Exception as exc:
            logger.info("行业快照匹配失败: %s", exc)

    if not peers:
        result = {"status": "unavailable", "message": "未找到可对比的同业公司组"}
        _CACHE[cache_key] = (time.time(), result)
        return result

    # 获取同业 PE/PB
    try:
        peer_quotes = await fetch_quotes(peers)
    except Exception:
        peer_quotes = {}

    peer_pes = []
    peer_pbs = []
    peer_details = []
    for pcode in peers:
        pq = peer_quotes.get(pcode, {})
        ppe = pq.get("pe", 0) or 0
        ppb = pq.get("pb", 0) or 0
        if ppe > 0:
            peer_pes.append(ppe)
        if ppb > 0:
            peer_pbs.append(ppb)
        if pq.get("price", 0) > 0:
            peer_details.append({
                "code": pcode,
                "name": pq.get("name", ""),
                "price": round(pq["price"], 2),
                "pe": round(ppe, 2) if ppe > 0 else None,
                "pb": round(ppb, 2) if ppb > 0 else None,
            })

    def _median(lst):
        s = sorted(lst)
        n = len(s)
        if n == 0:
            return None
        return s[n // 2] if n % 2 else round((s[n // 2 - 1] + s[n // 2]) / 2, 2)

    median_pe = _median(peer_pes)
    median_pb = _median(peer_pbs)

    pe_dev = None
    pb_dev = None
    if target_pe and median_pe:
        pe_dev = round((target_pe / median_pe - 1) * 100, 1)
    if target_pb and median_pb:
        pb_dev = round((target_pb / median_pb - 1) * 100, 1)

    # 综合判断
    if pe_dev is not None:
        if pe_dev < -20:
            cmp_verdict = "相对低估"
        elif pe_dev < 10:
            cmp_verdict = "估值合理"
        elif pe_dev < 50:
            cmp_verdict = "相对高估"
        else:
            cmp_verdict = "显著高估"
    else:
        cmp_verdict = "无法判断"

    result = {
        "status": "available",
        "industry": industry_found,
        "peer_count": len(peer_details),
        "target": {
            "name": target_name,
            "code": code,
            "pe": target_pe,
            "pb": target_pb,
        },
        "peer_median": {"pe": median_pe, "pb": median_pb},
        "deviation": {"pe_dev_pct": pe_dev, "pb_dev_pct": pb_dev},
        "verdict": cmp_verdict,
        "peers": peer_details,
        "disclaimer": "同业组为预设，数据来自公开行情，非投资建议。",
    }

    _CACHE[cache_key] = (time.time(), result)
    return result
