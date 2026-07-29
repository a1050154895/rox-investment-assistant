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
    """个股框架分析"""
    if code not in STOCKS:
        return {"error": "未找到该股票"}

    # 框架一致性评分
    scores = {
        "contradiction": random.randint(55, 90),   # 矛盾分析 30%
        "value_law": random.randint(50, 88),        # 价值规律 35%
        "macro_cycle": random.randint(45, 85),      # 宏观周期 25%
        "technical": random.randint(40, 80),        # 技术分析 5%
        "discipline": random.randint(60, 95),        # 纪律 5%
    }
    total = round(
        scores["contradiction"] * 0.30 +
        scores["value_law"] * 0.35 +
        scores["macro_cycle"] * 0.25 +
        scores["technical"] * 0.05 +
        scores["discipline"] * 0.05
    )

    return {
        "code": code,
        "name": STOCKS[code]["name"],
        "consistency_score": total,
        "score_label": "高" if total >= 75 else ("较高" if total >= 60 else ("中等" if total >= 45 else "低")),
        "dimensions": {
            "contradiction": {"score": scores["contradiction"], "weight": 30, "label": "矛盾分析",
                              "detail": "主要矛盾强度适中，次要矛盾趋缓"},
            "value_law": {"score": scores["value_law"], "weight": 35, "label": "价值规律",
                          "detail": "剩余价值率稳定，资本有机构成适中"},
            "macro_cycle": {"score": scores["macro_cycle"], "weight": 25, "label": "宏观周期",
                            "detail": "处于流转阶段，产业资本活跃"},
            "technical": {"score": scores["technical"], "weight": 5, "label": "技术分析",
                          "detail": "MA20上方运行，量能温和放大"},
            "discipline": {"score": scores["discipline"], "weight": 5, "label": "纪律",
                           "detail": "符合334建仓节奏，仓位合理"},
        },
        "contradictions": {
            "primary": {"name": "行业集中度提升 vs 竞争加剧", "intensity": 68},
            "secondary": {"name": "需求复苏 vs 成本上行", "intensity": 52},
        },
        "value_assessment": {
            "surplus_rate": round(random.uniform(15, 45), 1),
            "organic_composition": round(random.uniform(2, 8), 1),
            "turnover_rate": round(random.uniform(0.3, 1.2), 2),
            "pricing_power": random.choice(["强", "中", "弱"]),
        },
        "fund_flow": {
            "main_inflow": round(random.uniform(-5, 15), 2),
            "trend": [round(random.uniform(-2, 3), 2) for _ in range(10)],
            "sector_comparison": round(random.uniform(-1, 2), 2),
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
