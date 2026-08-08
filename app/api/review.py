"""每日复盘 API。"""
from fastapi import APIRouter, Query

from app.services.review_engine import get_daily_review, get_review_history

router = APIRouter()


@router.get("/daily")
async def daily_review(force: bool = Query(False, description="强制刷新缓存")):
    """获取今日复盘数据：指数、涨跌统计、板块资金流、情绪评分、复盘摘要。"""
    return await get_daily_review(force=force)


@router.get("/history")
async def review_history(days: int = Query(7, ge=1, le=30, description="天数")):
    """获取近 N 个交易日的历史复盘摘要。"""
    return {"history": await get_review_history(days)}
