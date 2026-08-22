"""宏观代理矩阵 API。"""
from fastapi import APIRouter

from app.services.data_contract import ensure_contract
from app.services.macro_data import get_macro_matrix

router = APIRouter()


@router.get("/matrix")
async def matrix(refresh: bool = False):
    return ensure_contract(await get_macro_matrix(force=refresh), data_source="国家统计局/央行（AKShare）")
