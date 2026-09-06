"""宏观行业漏斗 API — 过滤器，不是推荐器。"""
from fastapi import APIRouter, Query

from app.services.macro_funnel import get_candidate_pool, get_funnel_ranking

router = APIRouter()


@router.get("/macro-industry")
async def funnel_macro_industry():
    """宏观状态 → 行业排序：方法论规则匹配 + 实测资金流参考。"""
    return await get_funnel_ranking()


@router.get("/candidate-pool")
async def funnel_candidate_pool(
    board: str = Query(..., min_length=2, max_length=20, description="东财行业板块名"),
    size: int = Query(8, ge=1, le=30),
):
    """目标行业的候选样本（流通市值降序）。候选池非投资建议。"""
    return await get_candidate_pool(board, size)
