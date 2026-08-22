"""研究卡 API：研究、论证、风控和决策的最小闭环。"""
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import JournalEntry, ResearchCard, User, utcnow

router = APIRouter()

# 研究卡完整生命周期：草稿 → 研究 → 验证 → 决策 → 观察 → 复盘 → 失效/归档
CARD_STATUSES = {
    "draft": "草稿",
    "researching": "研究中",
    "to_verify": "待验证",
    "ready": "待决策",
    "watching": "观察中",
    "reviewed": "已复盘",
    "invalidated": "已失效",
    "archived": "已归档",
}

HYPOTHESIS_STATUSES = {"成立", "部分成立", "失效", "未验证"}


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

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value: str) -> str:
        if value not in CARD_STATUSES:
            raise ValueError(f"status 必须是 {sorted(CARD_STATUSES)} 之一")
        return value

    @field_validator("hypothesis_status")
    @classmethod
    def _valid_hypothesis(cls, value: str | None) -> str | None:
        if value is not None and value not in HYPOTHESIS_STATUSES:
            raise ValueError(f"hypothesis_status 必须是 {sorted(HYPOTHESIS_STATUSES)} 之一")
        return value


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


def card_out(card: ResearchCard) -> dict:
    """研究卡序列化：附上状态中文标签和证据计数。"""
    data = card.to_dict()
    facts = data.get("facts") or []
    data["status_label"] = CARD_STATUSES.get(card.status, card.status)
    data["evidence_counts"] = {
        "facts": sum(1 for f in facts if not f.startswith("[待验证]")),
        "pending_verify": sum(1 for f in facts if f.startswith("[待验证]")),
        "counter": len([line for line in (card.counter_evidence or "").splitlines() if line.strip()]),
    }
    return data


def _risk_checks(card: ResearchCard) -> list[dict]:
    return [
        {"key": "question", "label": "研究问题", "passed": bool(card.question.strip())},
        {"key": "hypothesis", "label": "核心假设", "passed": bool(card.hypothesis.strip())},
        {"key": "facts", "label": "至少一条事实", "passed": bool(card.facts_json and card.facts_json != "[]")},
        {"key": "counter_evidence", "label": "反证", "passed": bool(card.counter_evidence.strip())},
        {"key": "invalidation", "label": "失效条件", "passed": bool(card.invalidation.strip())},
    ]


@router.get("/templates")
async def list_templates():
    """研究卡模板：只给问法和证据清单，不给结论。"""
    from app.services.research_templates import RESEARCH_TEMPLATES
    return {"templates": [
        {"id": tid, "name": t["name"], "description": t["description"]}
        for tid, t in RESEARCH_TEMPLATES.items()
    ]}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """获取研究卡模板预填内容（仅问法与证据清单，无结论）。"""
    from app.services.research_templates import RESEARCH_TEMPLATES
    tpl = RESEARCH_TEMPLATES.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"id": template_id, "name": tpl["name"], "seed": tpl["seed"]}


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
    today_str = date.today().isoformat()
    due = [card for card in cards if card.next_review_at and card.next_review_at <= today_str]
    return {
        "cards": [card_out(card) for card in cards],
        "due_review_cards": [card_out(card) for card in due],
        "pending_reviews": [entry.to_dict() for entry in pending_reviews],
        "next_action": "先处理到期复核，再补齐事实、假设和反证" if due else ("继续补齐事实、假设和反证" if cards else "创建第一张研究卡"),
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
    return {"count": len(cards), "cards": [card_out(card) for card in cards]}


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
    return {"success": True, "card": card_out(card)}


@router.get("/{card_id}")
async def get_card(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(ResearchCard).filter(ResearchCard.id == card_id, ResearchCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="研究卡不存在")
    return {"card": card_out(card)}


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
    return {"success": True, "card": card_out(card)}


class EvidenceIn(BaseModel):
    """跨页面证据抽屉提交的一条证据。"""
    evidence_type: str = Field(..., pattern="^(fact|counter|to_verify)$")
    content: str = Field(..., min_length=1, max_length=500)
    source: str = Field("", max_length=120)
    as_of: str = Field("", max_length=40)


@router.post("/{card_id}/evidence")
async def add_evidence(
    card_id: int,
    data: EvidenceIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """把情报/行情/宏观数据追加进已有研究卡：fact=事实，counter=反证，to_verify=待验证。"""
    card = db.query(ResearchCard).filter(ResearchCard.id == card_id, ResearchCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="研究卡不存在")

    meta = "（来源：" + " · ".join(p for p in (data.source, data.as_of) if p) + "）" if (data.source or data.as_of) else ""
    entry = f"{data.content}{meta}"

    if data.evidence_type == "counter":
        new_text = "\n".join(part for part in (card.counter_evidence.strip(), f"[反证] {entry}") if part)
        if len(new_text) > 2000:
            raise HTTPException(status_code=400, detail="反证内容已满，请先整理后再添加")
        card.counter_evidence = new_text
    else:
        prefix = "[待验证] " if data.evidence_type == "to_verify" else "[事实] "
        facts = json.loads(card.facts_json or "[]")
        if len(facts) >= 20:
            raise HTTPException(status_code=400, detail="事实条目已满（最多 20 条），请先整理后再添加")
        facts.append(prefix + entry)
        card.facts_json = json.dumps(facts, ensure_ascii=False)
    card.updated_at = utcnow()
    db.commit()
    db.refresh(card)
    return {"success": True, "card": card_out(card)}


@router.get("/{card_id}/detail")
async def card_detail(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """研究卡完整档案：证据、关联决策、执行结果、假设状态和复核提醒。"""
    card = db.query(ResearchCard).filter(ResearchCard.id == card_id, ResearchCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="研究卡不存在")
    decisions = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user.id, JournalEntry.research_card_id == card_id)
        .order_by(JournalEntry.date.desc(), JournalEntry.id.desc())
        .all()
    )
    settled = [d for d in decisions if d.result in ("盈", "亏")]
    wins = [d for d in settled if d.result == "盈"]
    pcts = [d.result_pct for d in settled if d.result_pct is not None]
    checks = _risk_checks(card)
    today_str = date.today().isoformat()
    return {
        "card": card_out(card),
        "decisions": [entry.to_dict() for entry in decisions],
        "decision_stats": {
            "total": len(decisions),
            "settled": len(settled),
            "wins": len(wins),
            "win_rate": round(len(wins) / len(settled) * 100, 1) if settled else None,
            "avg_result_pct": round(sum(pcts) / len(pcts), 2) if pcts else None,
        },
        "review_due": bool(card.next_review_at and card.next_review_at <= today_str),
        "risk": {
            "passed": sum(c["passed"] for c in checks),
            "total": len(checks),
            "checks": checks,
        },
    }


@router.get("/{card_id}/risk-check")
async def risk_check(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(ResearchCard).filter(ResearchCard.id == card_id, ResearchCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="研究卡不存在")
    checks = _risk_checks(card)
    passed = sum(item["passed"] for item in checks)
    return {
        "card_id": card.id,
        "status": "ready" if passed == len(checks) else "incomplete",
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "message": "研究条件已基本齐备" if passed == len(checks) else "先补齐失败项，再记录正式决策",
    }
