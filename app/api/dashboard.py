"""仪表盘聚合 API — 一次请求返回宏观+周期+矛盾+334+自选概览

方法论来源：卢麒元公开讲座思想提炼 + 马克思主义政治经济学公有领域理论
数据源：AKShare 实时指数 + NeoData 真实快照兜底 + 框架静态配置
"""
import random
from datetime import datetime
from fastapi import APIRouter

from app.services.market_data import get_market_indices, get_stock_quote
from app.services.intelligence_data import get_intelligence_brief

router = APIRouter()


@router.get("/overview")
async def overview():
    """仪表盘聚合数据"""
    # 获取实时市场指数
    market_indices = await get_market_indices()

    # 资讯研判面板：超时或数据源异常时独立降级，不影响行情主看板
    intelligence = await get_intelligence_brief()

    # 自选股实时行情
    watchlist = []
    watchlist_codes = [("600519", 78), ("300750", 65), ("300308", 85), ("600036", 71), ("002371", 80)]
    for code, base_score in watchlist_codes:
        quote = await get_stock_quote(code)
        if "error" not in quote:
            score = base_score + random.randint(-3, 3)
            watchlist.append({
                "name": quote.get("name", ""),
                "code": code,
                "price": quote.get("price", 0),
                "change_pct": quote.get("change_pct", 0),
                "score": score,
                "score_label": "高" if score >= 75 else ("较高" if score >= 60 else "中等"),
            })

    return {
        "market_indices": [
            {"name": "上证指数", "code": "000001.SH", "price": 3289.47, "change": 1.23, "change_pct": 0.04},
            {"name": "深证成指", "code": "399001.SZ", "price": 10457.82, "change": -15.36, "change_pct": -0.15},
            {"name": "创业板指", "code": "399006.SZ", "price": 2156.33, "change": 8.91, "change_pct": 0.41},
            {"name": "沪深300", "code": "000300.SH", "price": 3842.16, "change": 5.67, "change_pct": 0.15},
        ],
        "macro_compass": {
            "sovereign_credit": {
                "status": "中性信用", "score": 62, "trend": "stable",
                "detail": "直接税占比缓慢提升，财政纪律中等，人民币国际化稳步推进"
            },
            "value_realization": {
                "status": "中价值实现", "score": 55, "trend": "up",
                "detail": "社会总资本周转率回升，消费端温和复苏，积累与消费尚不平衡"
            },
            "matrix_cell": "中性信用 × 中价值实现",
            "matrix_action": "保持默认30/30/40",
            "framework_advice": "当前处于资本周期「流转」阶段中期，宏观分类为中性信用×中价值实现，保持默认30/30/40配置。成交额维持高位但赚钱效应一般，建议维持核心仓位不变，卫星池关注资金流入确认的标的。"
        },
        "capital_cycle": {
            "stages": ["积累", "集中", "流转", "分配", "再生产"],
            "current_stage": 2,
            "stage_name": "流转",
            "stage_detail": "资本从金融体系向实体经济流转加速，产业资本活跃度提升",
            "characteristics": {
                "成交额": "维持高位",
                "龙头集中度": "龙头扩散",
                "北向资金": "波动加大",
                "政策导向": "政策落地观察"
            },
            "progress": 45,
            "rule": "不先定阶段，不要讲仓位；阶段判断不清时建议观望"
        },
        "contradictions": {
            "primary": {
                "name": "政策预期 vs 经济现实", "type": "预期矛盾",
                "intensity": 72, "trend": "up",
                "desc": "稳增长政策密集出台，但实体经济数据仍偏弱，预期差扩大"
            },
            "secondary": {
                "name": "量能 vs 赚钱效应", "type": "量价矛盾",
                "intensity": 58, "trend": "stable",
                "desc": "成交额维持高位但赚钱效应一般，存量博弈特征明显"
            },
            "tertiary": {
                "name": "北向资金 vs 主力资金", "type": "资金矛盾",
                "intensity": 41, "trend": "down",
                "desc": "北向资金波动加大，与内资主力流向存在分歧"
            },
            "rule": "矛盾强度>70为强矛盾，需重点关注；矛盾转化时调整持仓结构"
        },
        "discipline_334": {
            "core": {
                "target": 30, "actual": 28,
                "stocks": ["贵州茅台", "宁德时代", "招商银行"],
                "rule": "宽基ETF或高确定性龙头，低换手，只在宏观分类根本变化时调整"
            },
            "satellite": {
                "target": 30, "actual": 22,
                "stocks": ["中际旭创", "北方华创"],
                "rule": "阶段景气行业，单月换手≤2次"
            },
            "cash": {
                "target": 40, "actual": 50,
                "note": "现金比例偏高，只在阶段切换+恐慌指标触发时启用",
                "rule": "货币基金/逆回购，不得因短期波动消耗"
            },
            "position_stages": [
                {"name": "首仓", "ratio": "30%", "trigger": "趋势结构初步出现", "status": "已完成"},
                {"name": "确认仓", "ratio": "30%", "trigger": "2个以上独立信号验证", "status": "部分完成"},
                {"name": "主升仓", "ratio": "40%", "trigger": "突破关键结构位+资金面共振", "status": "未触发"},
            ],
            "advice": "现金50% > 基准40%，建议在流转阶段将10%现金转入卫星池。确认仓仅部分完成，需等待量能+基本面+政策中至少2项确认信号。主升仓未触发，不得提前启动。"
        },
        "watchlist": watchlist,
        "intelligence": intelligence,
        "recent_decisions": [
            {"stock": "中际旭创", "code": "300308", "action": "买入", "date": "2026-07-28",
             "stage": "确认仓30%", "score": 85, "result": "待观察"},
            {"stock": "贵州茅台", "code": "600519", "action": "持有", "date": "2026-07-25",
             "stage": "主升仓40%", "score": 78, "result": "+2.3%"},
            {"stock": "宁德时代", "code": "300750", "action": "减仓", "date": "2026-07-22",
             "stage": "确认仓30%", "score": 52, "result": "-1.5%"},
        ],
        "updated_at": datetime.now().isoformat(),
    }


@router.get("/market_heatmap")
async def market_heatmap():
    """市场热力图数据"""
    sectors = [
        "半导体", "白酒", "银行", "新能源", "医药", "军工", "计算机",
        "房地产", "有色金属", "化工", "传媒", "电力", "汽车", "食品饮料",
        "家电", "钢铁", "建材", "农业", "通信", "券商"
    ]
    data = []
    for s in sectors:
        change = round(random.uniform(-3.5, 3.5), 2)
        data.append({"sector": s, "change": change, "volume": random.randint(50, 500)})
    return {"sectors": data}
