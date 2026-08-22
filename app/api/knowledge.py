"""本地知识库 API — 用户自供文件的检索，不外发、不进 AI 默认上下文。"""
from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.models import User
from app.services.knowledge_base import rebuild, search, status

router = APIRouter()


@router.get("/status")
async def kb_status(user: User = Depends(get_current_user)):
    return status()


@router.get("/search")
async def kb_search(
    q: str = Query(..., min_length=1, max_length=100, description="检索关键词"),
    limit: int = Query(8, ge=1, le=20),
    user: User = Depends(get_current_user),
):
    return search(q, limit)


@router.post("/rebuild")
async def kb_rebuild(user: User = Depends(get_current_user)):
    """手动重建索引（新增文件后调用）。"""
    return {"success": True, **rebuild()}
