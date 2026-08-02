"""决策日志 API — CRUD + 统计 + 复盘（数据库持久化，按用户隔离）。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import JournalEntry, User

router = APIRouter()


class DecisionCreate(BaseModel):
    stock: str = Field(..., max_length=20)
    code: str = Field(..., max_length=10)
    action: str = Field(..., description="买入/卖出/持有/减仓")
    stage: str = Field(..., description="试仓30%/确认30%/主力40%")
    cycle_stage: str = Field("流转", description="积累/集中/流转/分配/再生产")
    contradiction_intensity: int = Field(50, ge=0, le=100)
    value_realization: int = Field(50, ge=0, le=100)
    consistency_score: int = Field(50, ge=0, le=100)
    reason: str = Field("", max_length=500)


class DecisionUpdate(BaseModel):
    result: str | None = None
    result_pct: float | None = None
    review: str | None = None


def _entry_to_dict(e: JournalEntry) -> dict:
    return e.to_dict()


@router.get("/")
async def list_decisions(
    action: str = Query("", description="筛选操作类型"),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询当前用户的决策列表（按日期倒序）。"""
    q = db.query(JournalEntry).filter(JournalEntry.user_id == user.id)
    if action:
        q = q.filter(JournalEntry.action == action)
    rows = q.order_by(JournalEntry.date.desc(), JournalEntry.id.desc()).limit(limit).all()
    return {"total": len(rows), "decisions": [_entry_to_dict(r) for r in rows]}


@router.post("/")
async def create_decision(
    decision: DecisionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建决策记录。"""
    entry = JournalEntry(
        user_id=user.id,
        date=datetime.now().strftime("%Y-%m-%d"),
        result="待观察",
        result_pct=None,
        holding_days=0,
        review=None,
        **decision.model_dump(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"success": True, "id": entry.id, "decision": _entry_to_dict(entry)}


@router.get("/{decision_id}")
async def get_decision(
    decision_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单条决策详情（仅本人可见）。"""
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == decision_id, JournalEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="未找到该决策记录")
    return _entry_to_dict(entry)


@router.put("/{decision_id}")
async def update_decision(
    decision_id: int,
    update: DecisionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新决策记录（补充事后结果/复盘）。"""
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == decision_id, JournalEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="未找到该决策记录")
    if update.result is not None:
        entry.result = update.result
    if update.result_pct is not None:
        entry.result_pct = update.result_pct
    if update.review is not None:
        entry.review = update.review
    db.commit()
    db.refresh(entry)
    return {"success": True, "decision": _entry_to_dict(entry)}


@router.delete("/{decision_id}")
async def delete_decision(
    decision_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除决策记录。"""
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == decision_id, JournalEntry.user_id == user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="未找到该决策记录")
    db.delete(entry)
    db.commit()
    return {"success": True}


@router.get("/stats/summary")
async def stats_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """统计概览（当前用户）。"""
    rows = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).all()
    total = len(rows)
    scored = [r for r in rows if r.consistency_score]
    avg_score = round(sum(r.consistency_score for r in scored) / max(len(scored), 1), 1)
    high_consistency = len([r for r in rows if r.consistency_score >= 70])
    compliance_rate = round(high_consistency / max(total, 1) * 100, 1)

    wins = [r for r in rows if r.result == "盈"]
    losses = [r for r in rows if r.result == "亏"]
    win_rate = round(len(wins) / max(len(wins) + len(losses), 1) * 100, 1)

    low_score = [r for r in rows if r.consistency_score < 60]
    error_patterns = "存在低一致性记录，请逐条复核证据与纪律" if low_score else "暂无足够样本识别错误模式"

    return {
        "total": total,
        "avg_consistency": avg_score,
        "compliance_rate": compliance_rate,
        "win_rate": win_rate,
        "wins": len(wins),
        "losses": len(losses),
        "pending": len([r for r in rows if r.result == "待观察"]),
        "common_error": error_patterns,
        "score_distribution": {
            "high": len([r for r in rows if r.consistency_score >= 75]),
            "medium": len([r for r in rows if 45 <= r.consistency_score < 75]),
            "low": len([r for r in rows if r.consistency_score < 45]),
        },
    }


@router.post("/review")
async def generate_review(
    start_date: str = Query("2026-07-01"),
    end_date: str = Query("2026-07-31"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成复盘报告（当前用户数据）。"""
    rows = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id,
        JournalEntry.date >= start_date,
        JournalEntry.date <= end_date,
    ).all()
    total = len(rows)
    wins = [r for r in rows if r.result == "盈"]
    losses = [r for r in rows if r.result == "亏"]
    avg_score = round(sum(r.consistency_score for r in rows) / max(total, 1), 1)

    stage_stats: dict = {}
    for r in rows:
        stage = r.cycle_stage
        if stage not in stage_stats:
            stage_stats[stage] = {"count": 0, "wins": 0, "avg_score": 0, "scores": []}
        stage_stats[stage]["count"] += 1
        if r.result == "盈":
            stage_stats[stage]["wins"] += 1
        stage_stats[stage]["scores"].append(r.consistency_score)

    for s in stage_stats.values():
        s["avg_score"] = round(sum(s["scores"]) / max(len(s["scores"]), 1), 1)
        s["win_rate"] = round(s["wins"] / max(s["count"], 1) * 100, 1)
        del s["scores"]

    return {
        "period": f"{start_date} ~ {end_date}",
        "total_decisions": total,
        "wins": len(wins),
        "losses": len(losses),
        "pending": total - len(wins) - len(losses),
        "avg_consistency": avg_score,
        "total_return": round(sum(r.result_pct or 0 for r in rows), 2),
        "stage_breakdown": stage_stats,
        "insights": ["当前样本不足，无法得出稳定胜率或阶段有效性结论"] if total < 10 else [
            "请结合样本量、市场环境和最大回撤评估框架表现",
            "一致性评分只反映纪律匹配，不代表未来收益",
        ],
        "suggestions": [
            "持续记录事实依据、数据来源、建仓触发和退出条件",
            "至少积累10条已完成决策后再评估统计结果",
        ],
    }
