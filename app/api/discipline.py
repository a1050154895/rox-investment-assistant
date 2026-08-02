"""用户 334 仓位纪律评估 API — 评估为纯函数（公开），档案按用户持久化。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import DisciplineProfile as DBDisciplineProfile, User
from app.services.discipline_engine import evaluate_discipline

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
