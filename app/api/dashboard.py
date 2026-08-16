"""仪表盘聚合 API — 一次请求返回宏观+周期+矛盾+334+自选概览

方法论来源：卢麒元公开讲座思想提炼 + 马克思主义政治经济学公有领域理论
数据源：AKShare 实时指数 + NeoData 真实快照兜底 + 框架静态配置
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import Alert, JournalEntry, Position, User, Watchlist
from app.services.contradiction_engine import get_contradictions
from app.services.market_data import get_market_indices
from app.services.intelligence_data import get_intelligence_brief
from app.services.macro_data import get_macro_matrix
from app.services.review_engine import get_capital_cycle_stage
from app.services.tencent_data import fetch_quotes

router = APIRouter()


@router.get("/overview")
async def overview():
    """仪表盘聚合数据"""
    # 获取实时市场指数
    market_indices = await get_market_indices()

    # 资讯与宏观矩阵独立降级，任一外部数据源异常都不影响行情主看板
    intelligence, macro_matrix, capital_cycle, contradictions = await asyncio.gather(
        get_intelligence_brief(), get_macro_matrix(), get_capital_cycle_stage(), get_contradictions()
    )

    # 自选股实时行情 — 前端异步加载用户真实自选股，此处返回空数组
    watchlist = []

    return {
        "market_indices": market_indices,
        "macro_compass": macro_matrix,
        "capital_cycle": capital_cycle,
        "contradictions": contradictions,
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


@router.get("/stats")
async def user_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户综合统计 — 聚合决策、持仓、预警、自选股数据。"""
    # --- 决策日志统计 ---
    entries = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).all()
    total_decisions = len(entries)
    wins = [r for r in entries if r.result == "盈"]
    losses = [r for r in entries if r.result == "亏"]
    pending = [r for r in entries if r.result == "待观察"]
    scored = [r for r in entries if r.consistency_score]
    avg_consistency = round(sum(r.consistency_score for r in scored) / max(len(scored), 1), 1)
    win_rate = round(len(wins) / max(len(wins) + len(losses), 1) * 100, 1)

    # --- 持仓统计 ---
    positions = db.query(Position).filter(Position.user_id == user.id).all()
    pos_codes = [p.code for p in positions]
    quotes = await fetch_quotes(pos_codes) if pos_codes else {}
    total_cost = 0.0
    total_market = 0.0
    for p in positions:
        q = quotes.get(p.code, {})
        price = q.get("price", 0) or 0
        cost = p.shares * p.cost_price
        market = p.shares * price if price > 0 else cost
        total_cost += cost
        total_market += market
    total_pnl = total_market - total_cost
    total_pnl_pct = (total_market / total_cost - 1) * 100 if total_cost > 0 else 0

    # --- 预警统计 ---
    alerts = db.query(Alert).filter(Alert.user_id == user.id).all()
    active_alerts = [a for a in alerts if a.active]
    triggered_alerts = [a for a in alerts if a.triggered]

    # --- 自选股统计 ---
    watchlist_count = db.query(Watchlist).filter(Watchlist.user_id == user.id).count()

    return {
        "user": {"username": user.username, "plan": user.plan},
        "journal": {
            "total": total_decisions,
            "wins": len(wins),
            "losses": len(losses),
            "pending": len(pending),
            "win_rate": win_rate,
            "avg_consistency": avg_consistency,
        },
        "portfolio": {
            "count": len(positions),
            "total_cost": round(total_cost, 2),
            "total_market": round(total_market, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
        },
        "alerts": {
            "total": len(alerts),
            "active": len(active_alerts),
            "triggered": len(triggered_alerts),
        },
        "watchlist": {
            "count": watchlist_count,
        },
        "updated_at": datetime.now().isoformat(),
    }
