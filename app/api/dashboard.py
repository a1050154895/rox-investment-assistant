"""仪表盘聚合 API — 一次请求返回宏观+周期+矛盾+334+自选概览

方法论来源：卢麒元公开讲座思想提炼 + 马克思主义政治经济学公有领域理论
数据源：AKShare 实时指数 + NeoData 真实快照兜底 + 框架静态配置
"""
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
            score = base_score
            watchlist.append({
                "name": quote.get("name", ""),
                "code": code,
                "price": quote.get("price", 0),
                "change_pct": quote.get("change_pct", 0),
                "score": score,
                "score_label": "观察评分" if quote.get("stale") else ("高" if score >= 75 else "较高" if score >= 60 else "中等"),
                "data_status": quote.get("data_status"), "data_source": quote.get("data_source"),
                "as_of": quote.get("as_of"), "stale": quote.get("stale", False),
            })

    return {
        "market_indices": market_indices,
        "macro_compass": {
            "sovereign_credit": {
                "status": "未评估", "score": 0, "trend": "unknown",
                "detail": "缺少经过授权和校验的财政、税收与信用数据"
            },
            "value_realization": {
                "status": "未评估", "score": 0, "trend": "unknown",
                "detail": "缺少经过授权和校验的消费、资本周转与分配数据"
            },
            "matrix_cell": "数据不足",
            "matrix_action": "不输出仓位建议",
            "framework_advice": "宏观矩阵尚未接入可靠数据源。本页面仅展示方法结构，不生成确定性仓位结论。"
        },
        "capital_cycle": {
            "stages": ["积累", "集中", "流转", "分配", "再生产"],
            "current_stage": None,
            "stage_name": "未评估",
            "stage_detail": "缺少可靠的成交结构、资金流和宏观数据，暂不判断周期阶段",
            "characteristics": {},
            "progress": 0,
            "rule": "不先定阶段，不要讲仓位；阶段判断不清时建议观望"
        },
        "contradictions": {
            "primary": {"name": "待真实数据验证", "type": "未评估", "intensity": 0, "trend": "unknown", "desc": "不使用模拟强度"},
            "secondary": {"name": "待真实数据验证", "type": "未评估", "intensity": 0, "trend": "unknown", "desc": "不使用模拟强度"},
            "tertiary": {"name": "待真实数据验证", "type": "未评估", "intensity": 0, "trend": "unknown", "desc": "不使用模拟强度"},
            "rule": "只有经过来源校验的数据才能进入矛盾强度计算"
        },
        "discipline_334": {
            "core": {
                "target": 30, "actual": 30, "stocks": [],
                "rule": "模型基准：宽基ETF或高确定性龙头，低换手"
            },
            "satellite": {
                "target": 30, "actual": 30, "stocks": [],
                "rule": "模型基准：阶段景气行业，单月换手≤2次"
            },
            "cash": {
                "target": 40, "actual": 40,
                "note": "模型基准，不代表用户真实仓位",
                "rule": "模型基准：货币基金/逆回购，不得因短期波动消耗"
            },
            "position_stages": [
                {"name": "首仓", "ratio": "30%", "trigger": "趋势结构初步出现", "status": "未评估"},
                {"name": "确认仓", "ratio": "30%", "trigger": "2个以上独立信号验证", "status": "未评估"},
                {"name": "主升仓", "ratio": "40%", "trigger": "突破关键结构位+资金面共振", "status": "未评估"},
            ],
            "advice": "当前仅展示334方法论基准；尚未接入用户真实持仓，不输出调仓建议。"
        },
        "watchlist": watchlist,
        "intelligence": intelligence,
        "recent_decisions": [],
        "updated_at": datetime.now().isoformat(),
    }


@router.get("/market_heatmap")
async def market_heatmap():
    """市场热力图数据；无可靠板块源时明确返回不可用。"""
    return {
        "sectors": [], "data_status": "unavailable", "stale": True,
        "message": "板块行情数据源尚未接入，系统不会生成模拟热力图。",
    }
