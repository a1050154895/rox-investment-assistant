"""宏观资讯与政策研判 API。"""
from fastapi import APIRouter, Query

from app.services.data_contract import ensure_contract
from app.services.intelligence_data import get_intelligence_brief, get_stock_intelligence
from app.services.market_data import get_stock_quote

router = APIRouter()


@router.get("/brief")
async def intelligence_brief(refresh: bool = Query(False, description="是否刷新资讯缓存")):
    """公开资讯、政策、全球风险、行业资金流的一体化研判简报。"""
    data = await get_intelligence_brief(force=refresh)
    return ensure_contract(
        data,
        status="realtime" if data.get("news") else "partial",
        data_source=data.get("source_status"),
    )


@router.get("/stock/{code}")
async def stock_intelligence(code: str):
    """个股所在行业与宏观资讯的传导路径。"""
    quote = await get_stock_quote(code)
    if "error" in quote:
        return quote
    return await get_stock_intelligence(code, quote.get("name", code), quote.get("industry", ""))
