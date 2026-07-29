"""个股透视 API — K线数据、框架分析、资金流向"""
import random
import math
from datetime import datetime, timedelta
from fastapi import APIRouter, Query

router = APIRouter()

# 模拟股票数据库
STOCKS = {
    "600519": {"name": "贵州茅台", "industry": "白酒", "price": 1689.50},
    "300750": {"name": "宁德时代", "industry": "新能源", "price": 182.30},
    "300308": {"name": "中际旭创", "industry": "通信", "price": 156.80},
    "600036": {"name": "招商银行", "industry": "银行", "price": 35.42},
    "002371": {"name": "北方华创", "industry": "半导体", "price": 312.60},
    "000858": {"name": "五粮液", "industry": "白酒", "price": 142.30},
    "601318": {"name": "中国平安", "industry": "保险", "price": 48.60},
    "002594": {"name": "比亚迪", "industry": "汽车", "price": 245.80},
}


@router.get("/search")
async def search_stocks(q: str = Query("", description="搜索关键词")):
    """搜索股票"""
    results = []
    for code, info in STOCKS.items():
        if q in code or q in info["name"] or q in info["industry"]:
            results.append({"code": code, "name": info["name"], "industry": info["industry"]})
    return {"results": results[:10]}


@router.get("/{code}")
async def stock_info(code: str):
    """个股基本信息"""
    if code not in STOCKS:
        return {"error": "未找到该股票", "code": code}
    info = STOCKS[code]
    return {
        "code": code,
        "name": info["name"],
        "industry": info["industry"],
        "price": info["price"],
        "change": round(random.uniform(-2, 2), 2),
        "change_pct": round(random.uniform(-1.5, 1.5), 2),
        "pe": round(random.uniform(8, 60), 1),
        "pb": round(random.uniform(1, 10), 2),
        "roe": round(random.uniform(5, 35), 1),
        "market_cap": f"{random.randint(100, 20000)}亿",
        "turnover": round(random.uniform(0.5, 5), 2),
    }


@router.get("/{code}/kline")
async def kline(code: str, period: str = Query("daily", description="周期: daily/weekly")):
    """K线数据"""
    if code not in STOCKS:
        return {"error": "未找到该股票"}

    base_price = STOCKS[code]["price"]
    days = 120 if period == "daily" else 52
    now = datetime.now()
    candles = []

    price = base_price * 0.85
    for i in range(days):
        date = now - timedelta(days=days - i)
        volatility = random.uniform(0.01, 0.035)
        open_p = price
        close_p = price * (1 + random.uniform(-volatility, volatility))
        high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.015))
        low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.015))
        volume = random.randint(50000, 500000)

        candles.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(open_p, 2),
            "close": round(close_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "volume": volume,
        })
        price = close_p

    # 最后一根K线收盘价接近真实价格
    if candles:
        candles[-1]["close"] = base_price
        candles[-1]["high"] = base_price * 1.01
        candles[-1]["low"] = base_price * 0.99

    return {
        "code": code,
        "name": STOCKS[code]["name"],
        "period": period,
        "candles": candles,
    }


@router.get("/{code}/analysis")
async def stock_analysis(code: str):
    """个股框架分析 — 基于五维度一致性评分体系

    评分权重：矛盾分析30% + 价值规律35% + 宏观周期25% + 技术分析5% + 纪律5%
    价值规律：基于ROE、增长率、风险溢价计算内在价值与偏离度
    矛盾分析：量价矛盾、资金矛盾、结构矛盾、预期矛盾
    """
    if code not in STOCKS:
        return {"error": "未找到该股票"}

    info = STOCKS[code]
    base_price = info["price"]

    # 模拟基本面数据
    roe = round(random.uniform(8, 30), 1)
    pe = round(random.uniform(10, 50), 1)
    pb = round(random.uniform(1, 8), 2)
    growth_rate = round(random.uniform(0.03, 0.20), 3)
    beta = round(random.uniform(0.7, 1.5), 2)

    # 价值规律分析：计算内在价值与偏离度
    risk_free_rate = 0.03
    market_risk_premium = 0.06
    required_return = risk_free_rate + beta * market_risk_premium

    if roe / 100 > required_return:
        growth_adjusted = min(growth_rate, 0.20)
        intrinsic_pb = (1 + growth_adjusted) * (roe / 100 / required_return)
    else:
        intrinsic_pb = roe / 100 / required_return

    book_value = base_price / pb if pb > 0 else base_price
    intrinsic_price = intrinsic_pb * book_value
    deviation_ratio = (base_price - intrinsic_price) / intrinsic_price if intrinsic_price > 0 else 0

    if deviation_ratio < -0.30:
        value_grade, value_signal = "深度低估", "strong_buy"
    elif deviation_ratio < -0.15:
        value_grade, value_signal = "低估", "buy"
    elif deviation_ratio < 0.15:
        value_grade, value_signal = "合理", "hold"
    elif deviation_ratio < 0.30:
        value_grade, value_signal = "高估", "sell"
    else:
        value_grade, value_signal = "严重高估", "strong_sell"

    # 框架一致性评分
    contradiction_score = random.randint(55, 90)
    value_score = min(95, max(40, int(70 + deviation_ratio * -50)))  # 低估=高分
    macro_score = random.randint(45, 85)
    technical_score = random.randint(40, 80)
    discipline_score = random.randint(60, 95)

    total = round(
        contradiction_score * 0.30 +
        value_score * 0.35 +
        macro_score * 0.25 +
        technical_score * 0.05 +
        discipline_score * 0.05
    )

    # 矛盾类型
    contradiction_types = [
        {"name": "量价矛盾", "desc": "量能 vs 赚钱效应", "intensity": random.randint(40, 80)},
        {"name": "资金矛盾", "desc": "北向资金 vs 主力资金", "intensity": random.randint(30, 70)},
        {"name": "结构矛盾", "desc": "行业分化 vs 指数共振", "intensity": random.randint(35, 65)},
        {"name": "预期矛盾", "desc": "政策预期 vs 经济现实", "intensity": random.randint(45, 75)},
    ]
    primary_contradiction = max(contradiction_types, key=lambda x: x["intensity"])

    return {
        "code": code,
        "name": info["name"],
        "consistency_score": total,
        "score_label": "高" if total >= 75 else ("较高" if total >= 60 else ("中等" if total >= 45 else "低")),
        "dimensions": {
            "contradiction": {"score": contradiction_score, "weight": 30, "label": "矛盾分析",
                              "detail": f"主要矛盾：{primary_contradiction['name']}（强度{primary_contradiction['intensity']}）"},
            "value_law": {"score": value_score, "weight": 35, "label": "价值规律",
                          "detail": f"偏离度{deviation_ratio:+.1%}，评级：{value_grade}"},
            "macro_cycle": {"score": macro_score, "weight": 25, "label": "宏观周期",
                            "detail": "处于流转阶段，产业资本活跃"},
            "technical": {"score": technical_score, "weight": 5, "label": "技术分析",
                          "detail": "辅助参考，MACD/RSI/KDJ综合判断"},
            "discipline": {"score": discipline_score, "weight": 5, "label": "纪律执行",
                           "detail": "334建仓节奏遵守程度"},
        },
        "contradictions": {
            "primary": {"name": primary_contradiction["name"], "intensity": primary_contradiction["intensity"],
                        "desc": primary_contradiction["desc"]},
            "secondary": {"name": contradiction_types[1]["name"], "intensity": contradiction_types[1]["intensity"]},
            "all_types": contradiction_types,
        },
        "value_assessment": {
            "intrinsic_price": round(intrinsic_price, 2),
            "current_price": base_price,
            "deviation_ratio": round(deviation_ratio, 4),
            "deviation_pct": f"{deviation_ratio:+.1%}",
            "value_grade": value_grade,
            "value_signal": value_signal,
            "roe": roe,
            "pe": pe,
            "pb": pb,
            "growth_rate": f"{growth_rate:.1%}",
            "required_return": f"{required_return:.1%}",
            "surplus_rate": round(roe * 0.6, 1),  # 剩余价值率近似
            "organic_composition": round(pb * 2, 1),  # 资本有机构成近似
            "turnover_rate": round(random.uniform(0.3, 1.2), 2),
            "pricing_power": random.choice(["强", "中", "弱"]),
        },
        "fund_flow": {
            "main_inflow": round(random.uniform(-5, 15), 2),
            "trend": [round(random.uniform(-2, 3), 2) for _ in range(10)],
            "sector_comparison": round(random.uniform(-1, 2), 2),
            "north_flow": round(random.uniform(-10, 20), 2),
        },
        "position_recommendation": {
            "stage": "确认仓30%" if total >= 60 else "首仓30%",
            "trigger": "2个以上独立信号验证" if total >= 60 else "趋势结构初步出现",
            "rule": "任意一段未触发，后面一段不能启动",
        },
    }


@router.get("/{code}/indicators")
async def indicators(code: str):
    """技术指标数据"""
    if code not in STOCKS:
        return {"error": "未找到该股票"}

    return {
        "code": code,
        "rsi": round(random.uniform(30, 75), 1),
        "kdj_j": round(random.uniform(-10, 100), 1),
        "macd": round(random.uniform(-1.5, 1.5), 3),
        "macd_signal": round(random.uniform(-1.2, 1.2), 3),
        "ma5": round(STOCKS[code]["price"] * random.uniform(0.97, 1.03), 2),
        "ma20": round(STOCKS[code]["price"] * random.uniform(0.90, 1.05), 2),
        "ma60": round(STOCKS[code]["price"] * random.uniform(0.85, 1.00), 2),
        "boll_upper": round(STOCKS[code]["price"] * 1.05, 2),
        "boll_lower": round(STOCKS[code]["price"] * 0.95, 2),
    }
