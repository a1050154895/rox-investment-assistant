"""异动雷达 API：波动率突破 + 成交量异动 + 新闻反查。"""
import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import User, Watchlist
from app.services.anomaly_scanner import intraday_scan, pre_market_scan, scan_stock, scan_watchlist

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
