"""研究卡 API：研究、论证、风控和决策的最小闭环。"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import JournalEntry, ResearchCard, User, utcnow

router = APIRouter()


class ResearchCardIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    code: str = Field("", max_length=10)
    stock: str = Field("", max_length=30)
    question: str = Field("", max_length=1000)
    hypothesis: str = Field("", max_length=2000)
    facts: list[str] = Field(default_factory=list, max_length=20)
    counter_evidence: str = Field("", max_length=2000)
    invalidation: str = Field("", max_length=1000)
    action: str = Field("观察", max_length=10)
    position_plan: str = Field("", max_length=80)
    stop_loss: float | None = None
    holding_period: str = Field("", max_length=30)
    status: str = Field("draft", max_length=20)
    hypothesis_status: str | None = Field(None, max_length=20)
    next_review_at: str | None = Field(None, max_length=10)


class ResearchCardUpdate(ResearchCardIn):
    title: str = Field(..., min_length=1, max_length=120)
    hypothesis_status: str | None = Field(None, max_length=20)
    next_review_at: str | None = Field(None, max_length=10)


def _set_card(card: ResearchCard, data: ResearchCardIn) -> None:
    values = data.model_dump(exclude={"facts"})
    for key, value in values.items():
        setattr(card, key, value)
    card.facts_json = json.dumps(data.facts, ensure_ascii=False)
    card.updated_at = utcnow()


@router.get("/today")
async def today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """今日研究队列：未完成研究卡、待复盘决策和下一步动作。"""
    cards = (
        db.query(ResearchCard)
        .filter(ResearchCard.user_id == user.id, ResearchCard.status != "archived")
        .order_by(ResearchCard.updated_at.desc(), ResearchCard.id.desc())
        .limit(8)
        .all()
    )
    pending_reviews = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user.id, JournalEntry.result == "待观察")
        .order_by(JournalEntry.date.desc(), JournalEntry.id.desc())
        .limit(5)
        .all()
    )
    return {
        "cards": [card.to_dict() for card in cards],
        "pending_reviews": [entry.to_dict() for entry in pending_reviews],
        "next_action": "继续补齐事实、假设和反证" if cards else "创建第一张研究卡",
    }


@router.get("/")
async def list_cards(
    status: str = Query("", max_length=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ResearchCard).filter(ResearchCard.user_id == user.id)
    if status:
        query = query.filter(ResearchCard.status == status)
    cards = query.order_by(ResearchCard.updated_at.desc(), ResearchCard.id.desc()).limit(100).all()
    return {"count": len(cards), "cards": [card.to_dict() for card in cards]}


@router.post("/")
async def create_card(
    data: ResearchCardIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = ResearchCard(user_id=user.id, title=data.title)
    _set_card(card, data)
    db.add(card)
    db.commit()
    db.refresh(card)
    return {"success": True, "card": card.to_dict()}


@router.get("/{card_id}")
async def get_card(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(ResearchCard).filter(ResearchCard.id == card_id, ResearchCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="研究卡不存在")
    return {"card": card.to_dict()}


@router.put("/{card_id}")
async def update_card(
    card_id: int,
    data: ResearchCardUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = db.query(ResearchCard).filter(ResearchCard.id == card_id, ResearchCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="研究卡不存在")
    _set_card(card, data)
    db.commit()
    db.refresh(card)
    return {"success": True, "card": card.to_dict()}


@router.get("/{card_id}/risk-check")
async def risk_check(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(ResearchCard).filter(ResearchCard.id == card_id, ResearchCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="研究卡不存在")
    checks = [
        {"key": "question", "label": "研究问题", "passed": bool(card.question.strip())},
        {"key": "hypothesis", "label": "核心假设", "passed": bool(card.hypothesis.strip())},
        {"key": "facts", "label": "至少一条事实", "passed": bool(card.facts_json and card.facts_json != "[]")},
        {"key": "counter_evidence", "label": "反证", "passed": bool(card.counter_evidence.strip())},
        {"key": "invalidation", "label": "失效条件", "passed": bool(card.invalidation.strip())},
    ]
    passed = sum(item["passed"] for item in checks)
    return {
        "card_id": card.id,
        "status": "ready" if passed == len(checks) else "incomplete",
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "message": "研究条件已基本齐备" if passed == len(checks) else "先补齐失败项，再记录正式决策",
    }
