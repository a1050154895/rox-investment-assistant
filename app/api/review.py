"""每日复盘 API。"""
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import JournalEntry, ResearchCard, User
from app.services.review_engine import get_daily_review, get_review_history

router = APIRouter()


@router.get("/daily")
async def daily_review(force: bool = Query(False, description="强制刷新缓存")):
    """获取今日复盘数据：指数、涨跌统计、板块资金流、情绪评分、复盘摘要。"""
    return await get_daily_review(force=force)


@router.get("/history")
async def review_history(days: int = Query(7, ge=1, le=30, description="天数")):
    """获取近 N 个交易日的历史复盘摘要。"""
    return {"history": await get_review_history(days)}


@router.get("/research-stats")
async def research_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """按当前用户的研究卡汇总决策结果，不把待观察样本计入胜率。"""
    cards = db.query(ResearchCard).filter(ResearchCard.user_id == user.id).all()
    decisions = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id,
        JournalEntry.research_card_id.isnot(None),
    ).all()
    card_ids = {card.id for card in cards}
    decisions = [entry for entry in decisions if entry.research_card_id in card_ids]

    wins = [entry for entry in decisions if entry.result == "盈"]
    losses = [entry for entry in decisions if entry.result == "亏"]
    settled = wins + losses
    scored = [entry.consistency_score for entry in decisions if entry.consistency_score is not None]
    by_action = defaultdict(lambda: {"total": 0, "wins": 0, "losses": 0, "pending": 0})
    for entry in decisions:
        bucket = by_action[entry.action or "未标注"]
        bucket["total"] += 1
        if entry.result == "盈":
            bucket["wins"] += 1
        elif entry.result == "亏":
            bucket["losses"] += 1
        else:
            bucket["pending"] += 1

    return {
        "cards": {
            "total": len(cards),
            "draft": sum(card.status == "draft" for card in cards),
            "ready": sum(card.status == "ready" for card in cards),
            "archived": sum(card.status == "archived" for card in cards),
        },
        "decisions": {
            "total": len(decisions),
            "pending": sum(entry.result not in ("盈", "亏") for entry in decisions),
            "settled": len(settled),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(settled) * 100, 1) if settled else None,
            "avg_consistency": round(sum(scored) / len(scored), 1) if scored else None,
            "avg_result_pct": round(sum(entry.result_pct for entry in settled if entry.result_pct is not None) / max(len([entry for entry in settled if entry.result_pct is not None]), 1), 2) if any(entry.result_pct is not None for entry in settled) else None,
        },
        "by_action": dict(by_action),
        "coverage": {
            "linked_cards": len({entry.research_card_id for entry in decisions}),
            "unlinked_cards": len(cards) - len({entry.research_card_id for entry in decisions}),
        },
    }
