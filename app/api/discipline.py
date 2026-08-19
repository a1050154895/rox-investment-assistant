"""用户 334 仓位纪律评估 API — 评估为纯函数（公开），档案按用户持久化。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import DisciplineProfile as DBDisciplineProfile, Position, User
from app.services.discipline_engine import build_health_report, evaluate_discipline
from app.services.review_engine import get_capital_cycle_stage
from app.services.tencent_data import fetch_quotes

router = APIRouter()


class DisciplineProfile(BaseModel):
    core_pct: float = Field(30, ge=0, le=100)
    satellite_pct: float = Field(30, ge=0, le=100)
    cash_pct: float = Field(40, ge=0, le=100)
    max_total_position_pct: float = Field(60, ge=0, le=100)
    single_trade_risk_pct: float = Field(1, gt=0, le=20)
    stop_loss_pct: float = Field(8, gt=0, le=100)
    single_position_limit_pct: float = Field(15, gt=0, le=100)
    sector_limit_pct: float = Field(30, gt=0, le=100)
    current_sector_exposure_pct: float = Field(0, ge=0, le=100)
    planned_position_pct: float = Field(0, ge=0, le=100)
    monthly_trades: int = Field(0, ge=0, le=1000)
    monthly_trade_limit: int = Field(2, ge=1, le=1000)
    operating_rules: str = Field("", max_length=2000)

    @model_validator(mode="after")
    def validate_allocation(self):
        total = self.core_pct + self.satellite_pct + self.cash_pct
        if total > 100.01:
            raise ValueError("核心、卫星与现金仓位合计不能超过100%")
        return self


@router.get("/defaults")
async def defaults():
    profile = DisciplineProfile()
    return {"profile": profile.model_dump(), "assessment": evaluate_discipline(profile.model_dump())}


@router.post("/evaluate")
async def evaluate(profile: DisciplineProfile):
    data = profile.model_dump()
    return {"profile": data, "assessment": evaluate_discipline(data)}


@router.get("/profile")
async def get_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取当前用户的 334 纪律档案（服务端持久化，跨设备同步）。"""
    row = db.query(DBDisciplineProfile).filter(DBDisciplineProfile.user_id == user.id).first()
    if not row:
        return {"profile": None}
    try:
        profile = json.loads(row.profile_json)
    except Exception:
        profile = None
    return {"profile": profile, "updated_at": row.updated_at.isoformat() if row.updated_at else None}


@router.put("/profile")
async def save_profile(
    profile: DisciplineProfile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存当前用户的 334 纪律档案到服务端。"""
    row = db.query(DBDisciplineProfile).filter(DBDisciplineProfile.user_id == user.id).first()
    payload = json.dumps(profile.model_dump(), ensure_ascii=False)
    if row:
        row.profile_json = payload
    else:
        row = DBDisciplineProfile(user_id=user.id, profile_json=payload)
        db.add(row)
    db.commit()
    return {"success": True, "profile": profile.model_dump(), "assessment": evaluate_discipline(profile.model_dump())}


@router.get("/assessment")
async def assessment(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """334 体检：合并真实持仓 + 当前资本周期阶段 + 纪律边界检查。"""
    # 1) 读取纪律档案（未保存时用默认 30/30/40）
    row = db.query(DBDisciplineProfile).filter(DBDisciplineProfile.user_id == user.id).first()
    profile = DisciplineProfile().model_dump()
    if row:
        try:
            profile = json.loads(row.profile_json)
        except Exception:
            profile = DisciplineProfile().model_dump()

    # 2) 读取真实持仓（行情缺失时以成本价兜底，不编造市值）
    positions = db.query(Position).filter(Position.user_id == user.id).all()
    codes = [p.code for p in positions]
    quotes = await fetch_quotes(codes) if codes else {}
    items = []
    total_cost = 0.0
    total_market = 0.0
    for p in positions:
        q = quotes.get(p.code, {})
        price = q.get("price", 0) or 0
        cost = p.shares * p.cost_price
        market = p.shares * price if price > 0 else cost
        total_cost += cost
        total_market += market
        items.append({
            "code": p.code,
            "name": q.get("name") or p.name,
            "shares": p.shares,
            "cost_price": p.cost_price,
            "price": round(price, 2) if price > 0 else None,
            "market": round(market, 2),
        })
    portfolio = {
        "count": len(items),
        "total_cost": round(total_cost, 2),
        "total_market": round(total_market, 2),
        "positions": items,
    }

    # 3) 读取当前资本周期阶段
    cycle = await get_capital_cycle_stage()

    return build_health_report(profile, portfolio, cycle)
