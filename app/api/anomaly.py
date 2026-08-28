"""异动雷达 API：波动率突破 + 成交量异动 + 新闻反查。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import User, Watchlist
from app.services.anomaly_scanner import pre_market_scan, scan_stock, scan_watchlist

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
        "updated_at": __import__("datetime").datetime.now().isoformat(),
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
