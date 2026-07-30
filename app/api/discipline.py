"""用户 334 仓位纪律评估 API。"""
from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

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
