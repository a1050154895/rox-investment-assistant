"""自选股 API — CRUD + 实时行情。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import User, Watchlist
from app.services.tencent_data import fetch_quotes

router = APIRouter()


class WatchlistIn(BaseModel):
    code: str = Field(..., min_length=6, max_length=10, description="6 位股票代码")
    name: str = Field(..., min_length=1, max_length=30, description="股票名称")


@router.get("/")
async def list_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出自选股并附带实时行情。"""
    items = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id)
        .order_by(Watchlist.sort_order, Watchlist.id)
        .all()
    )
    codes = [w.code for w in items]
    quotes = await fetch_quotes(codes) if codes else {}

    result = []
    for w in items:
        q = quotes.get(w.code, {})
        price = q.get("price", 0) or 0
        change_pct = q.get("change_pct", 0) or 0
        result.append({
            **w.to_dict(),
            "price": round(price, 2) if price > 0 else None,
            "change_pct": round(change_pct, 2) if change_pct else None,
            "price_name": q.get("name") or w.name,
        })

    return {"watchlist": result, "count": len(result)}


@router.post("/")
async def add_to_watchlist(data: WatchlistIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """添加自选股（重复添加返回已有记录）。"""
    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id, Watchlist.code == data.code.strip())
        .first()
    )
    if existing:
        return {"success": True, "watchlist": existing.to_dict(), "exists": True}

    # sort_order 自动递增
    max_order = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id)
        .order_by(Watchlist.sort_order.desc())
        .first()
    )
    next_order = (max_order.sort_order + 1) if max_order else 0

    item = Watchlist(
        user_id=user.id,
        code=data.code.strip(),
        name=data.name.strip(),
        sort_order=next_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "watchlist": item.to_dict()}


@router.delete("/{item_id}")
async def remove_from_watchlist(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """从自选股移除。"""
    item = (
        db.query(Watchlist)
        .filter(Watchlist.id == item_id, Watchlist.user_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="自选股不存在")
    db.delete(item)
    db.commit()
    return {"success": True}


@router.put("/reorder")
async def reorder_watchlist(
    order: list[int],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量调整自选股排序。order 为 watchlist id 列表，按列表顺序赋值 sort_order。"""
    for idx, item_id in enumerate(order):
        item = (
            db.query(Watchlist)
            .filter(Watchlist.id == item_id, Watchlist.user_id == user.id)
            .first()
        )
        if item:
            item.sort_order = idx
    db.commit()
    return {"success": True}
