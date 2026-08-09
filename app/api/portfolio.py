"""持仓组合 API — CRUD + 实时汇总(P&L)。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.limiter import limiter
from app.db import get_db
from app.models import Position, User
from app.services.tencent_data import fetch_quotes

router = APIRouter()


class PositionIn(BaseModel):
    code: str = Field(..., min_length=6, max_length=10, description="6 位股票代码")
    name: str = Field(..., min_length=1, max_length=30, description="股票名称")
    shares: float = Field(..., gt=0, description="持仓股数")
    cost_price: float = Field(..., gt=0, description="成本价")
    date: str = Field(..., min_length=8, max_length=10, description="建仓日期")
    notes: str = Field(default="", max_length=500)


@router.get("/")
async def list_positions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出当前用户所有持仓。"""
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
        pnl = market - cost
        pnl_pct = (price / p.cost_price - 1) * 100 if p.cost_price > 0 and price > 0 else 0
        total_cost += cost
        total_market += market
        items.append({
            "id": p.id,
            "code": p.code,
            "name": q.get("name") or p.name,
            "shares": p.shares,
            "cost_price": p.cost_price,
            "price": round(price, 2) if price > 0 else None,
            "cost": round(cost, 2),
            "market": round(market, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "date": p.date,
            "notes": p.notes,
        })

    total_pnl = total_market - total_cost
    total_pnl_pct = (total_market / total_cost - 1) * 100 if total_cost > 0 else 0

    return {
        "positions": items,
        "summary": {
            "count": len(items),
            "total_cost": round(total_cost, 2),
            "total_market": round(total_market, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
        },
    }


@router.post("/")
async def add_position(data: PositionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """新增持仓。"""
    pos = Position(
        user_id=user.id, code=data.code.strip(), name=data.name.strip(),
        shares=data.shares, cost_price=data.cost_price,
        date=data.date.strip(), notes=data.notes.strip(),
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return {"success": True, "position": pos.to_dict()}


@router.delete("/{pos_id}")
async def delete_position(pos_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除持仓。"""
    pos = db.query(Position).filter(Position.id == pos_id, Position.user_id == user.id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="持仓不存在")
    db.delete(pos)
    db.commit()
    return {"success": True}
