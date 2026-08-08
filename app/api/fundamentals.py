"""基本面 API：财务摘要、估值、质量评分、DCF、可比估值。"""
from fastapi import APIRouter, Query

from app.services.fundamentals_engine import get_comps_valuation, get_dcf_valuation, get_fundamentals

router = APIRouter()


@router.get("/{code}")
async def fundamentals(code: str, force: bool = Query(False, description="强制刷新缓存")):
    """获取个股基本面全貌：近5年财务摘要、实时估值、质量评分、投资要点。"""
    return await get_fundamentals(code, force=force)


@router.get("/{code}/dcf")
async def dcf_valuation(code: str, force: bool = Query(False, description="强制刷新")):
    """DCF 现金流折现估值：目标价、隐含涨跌幅、模型假设。"""
    return await get_dcf_valuation(code, force=force)


@router.get("/{code}/comps")
async def comps_valuation(code: str, force: bool = Query(False, description="强制刷新")):
    """可比公司估值：同业 PE/PB 中位数对比、偏离度。"""
    return await get_comps_valuation(code, force=force)
