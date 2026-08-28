"""基金/ETF研究透视 API。"""
from fastapi import APIRouter, Query

from app.services.data_contract import ensure_contract
from app.services.fund_data import get_fund, get_fund_kline, search_funds

router = APIRouter()


@router.get("/search")
async def fund_search(q: str = Query("", max_length=30)):
    return {"results": await search_funds(q)}


@router.get("/{code}")
async def fund_info(code: str):
    return ensure_contract(await get_fund(code))


@router.get("/{code}/kline")
async def fund_kline(code: str, period: str = Query("daily")):
    return ensure_contract(await get_fund_kline(code, period))
