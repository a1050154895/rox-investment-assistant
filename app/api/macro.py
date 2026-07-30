"""宏观代理矩阵 API。"""
from fastapi import APIRouter

from app.services.macro_data import get_macro_matrix

router = APIRouter()


@router.get("/matrix")
async def matrix(refresh: bool = False):
    return await get_macro_matrix(force=refresh)
