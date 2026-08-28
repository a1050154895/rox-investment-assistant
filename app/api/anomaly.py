"""异动雷达 API：波动率突破 + 成交量异动 + 新闻反查。"""
import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import AnomalyEvent, User, Watchlist, utcnow
from app.services.anomaly_scanner import (
    classify_event_status,
    event_status_label,
    intraday_scan,
    pre_market_scan,
    scan_stock,
    scan_watchlist,
)

router = APIRouter()


@router.get("/scan")
async def scan_anomalies(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """扫描当前用户自选股的异动状态。

    返回 {anomalies, scanned, updated_at}。
    anomalies: 有异动的标的列表，按强度排序。
    """
    wl = db.query(Watchlist).filter(
        Watchlist.user_id == user.id
    ).order_by(Watchlist.sort_order).all()
    items = [{"code": w.code, "name": w.name} for w in wl]
    anomalies = await scan_watchlist(items)
    return {
        "anomalies": anomalies,
        "scanned": len(items),
        "flagged": len(anomalies),
        "updated_at": datetime.now().isoformat(),
    }


@router.get("/stock/{code}")
async def scan_single(
    code: str,
    user: User = Depends(get_current_user),
):
    """扫描单只标的的异动详情（含新闻反查）。"""
    result = await scan_stock(code)
    if not result:
        return {"code": code, "available": False, "message": "数据不足或不可用"}
    return result


@router.get("/pre-market")
async def pre_market(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """盘前扫描：隔夜新闻 × 自选股交叉筛选。"""
    wl = db.query(Watchlist).filter(
        Watchlist.user_id == user.id
    ).order_by(Watchlist.sort_order).all()
    items = [{"code": w.code, "name": w.name} for w in wl]
    return await pre_market_scan(items)


@router.get("/intraday")
async def intraday(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """盘中异动扫描：分钟级 K 线检测自选股实时异动。"""
    wl = db.query(Watchlist).filter(
        Watchlist.user_id == user.id
    ).order_by(Watchlist.sort_order).all()
    items = [{"code": w.code, "name": w.name} for w in wl]

    semaphore = asyncio.Semaphore(3)

    async def _scan(w: dict):
        async with semaphore:
            return await intraday_scan(w["code"], w.get("name", ""))

    results = await asyncio.gather(*[_scan(w) for w in items])
    alerts = [r for r in results if r and r.get("intraday")]
    return {
        "alerts": alerts,
        "scanned": len(items),
        "flagged": len(alerts),
        "updated_at": datetime.now().isoformat(),
    }


def _event_snapshot(result: dict) -> dict:
    return {
        "observed_at": datetime.now().isoformat(),
        "price": result.get("price"),
        "change_pct": result.get("change_pct"),
        "range_ratio": result.get("range_ratio"),
        "volume_ratio": result.get("volume_ratio"),
        "flow_direction": result.get("flow_direction"),
        "max_volume_time": result.get("max_volume_time"),
        "max_range_time": result.get("max_range_time"),
        "news_relation": result.get("news_relation", "unmatched"),
    }


@router.get("/events")
async def list_events(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    events = db.query(AnomalyEvent).filter(
        AnomalyEvent.user_id == user.id,
    ).order_by(AnomalyEvent.updated_at.desc()).limit(50).all()
    return {"events": [dict(event.to_dict(), status_label=event_status_label(event.status)) for event in events]}


@router.post("/events")
async def create_event(
    code: str,
    name: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await intraday_scan(code, name)
    if not result or not result.get("intraday"):
        return {"available": False, "message": "当前没有可记录的盘中异动"}
    snapshot = _event_snapshot(result)
    event = AnomalyEvent(
        user_id=user.id,
        code=code,
        name=result.get("name", name),
        status="detected",
        snapshots_json=json.dumps([snapshot], ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return dict(event.to_dict(), status_label=event_status_label(event.status))


@router.post("/events/{event_id}/refresh")
async def refresh_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = db.query(AnomalyEvent).filter(
        AnomalyEvent.id == event_id,
        AnomalyEvent.user_id == user.id,
    ).first()
    if not event:
        return {"error": "事件不存在"}
    result = await intraday_scan(event.code, event.name)
    snapshots = json.loads(event.snapshots_json or "[]")
    if result and result.get("intraday"):
        snapshots.append(_event_snapshot(result))
    event.snapshots_json = json.dumps(snapshots[-20:], ensure_ascii=False)
    event.status = classify_event_status(snapshots)
    event.updated_at = utcnow()
    db.commit()
    db.refresh(event)
    return dict(event.to_dict(), status_label=event_status_label(event.status), available=bool(result))
