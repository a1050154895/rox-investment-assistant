"""基本面 API：财务摘要、估值、质量评分。"""
from fastapi import APIRouter, Query

from app.services.fundamentals_engine import get_fundamentals

router = APIRouter()


@router.get("/{code}")
async def fundamentals(code: str, force: bool = Query(False, description="强制刷新缓存")):
    """获取个股基本面全貌：近5年财务摘要、实时估值、质量评分、投资要点。"""
    return await get_fundamentals(code, force=force)
