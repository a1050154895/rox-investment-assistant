"""价格预警 API — CRUD + 触发检测。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import Alert, User
from app.services.tencent_data import fetch_quotes

router = APIRouter()


class AlertIn(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)
    name: str = Field(..., min_length=1, max_length=30)
    target_price: float = Field(..., gt=0)
    direction: str = Field("above", pattern="^(above|below)$")


@router.get("/")
async def list_alerts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出所有预警，并实时检测触发状态。"""
    alerts = db.query(Alert).filter(Alert.user_id == user.id).all()
    codes = list({a.code for a in alerts})
    quotes = await fetch_quotes(codes) if codes else {}
    updated = False

    items = []
    for a in alerts:
        q = quotes.get(a.code, {})
        price = q.get("price", 0) or 0
        triggered = False
        if price > 0 and a.active:
            if a.direction == "above" and price >= a.target_price:
                triggered = True
            elif a.direction == "below" and price <= a.target_price:
                triggered = True
        if triggered and not a.triggered:
            a.triggered = True
            a.triggered_at = datetime.utcnow()
            updated = True
        items.append({
            **a.to_dict(),
            "current_price": round(price, 2) if price > 0 else None,
            "price_name": q.get("name") or a.name,
        })

    if updated:
        db.commit()

    return {"alerts": items, "count": len(items)}


@router.post("/")
async def create_alert(data: AlertIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建预警。"""
    alert = Alert(
        user_id=user.id, code=data.code.strip(), name=data.name.strip(),
        target_price=data.target_price, direction=data.direction,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"success": True, "alert": alert.to_dict()}


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除预警。"""
    a = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="预警不存在")
    db.delete(a)
    db.commit()
    return {"success": True}
