"""本地知识库 API — 用户自供文件的检索 + 内置操作指引，不外发、不进 AI 默认上下文。"""
from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.models import User
from app.services import knowledge_playbooks
from app.services.knowledge_base import rebuild, search, status

router = APIRouter()


@router.get("/status")
async def kb_status(user: User = Depends(get_current_user)):
    return {**status(), "playbooks": knowledge_playbooks.list_playbooks()["count"]}


@router.get("/search")
async def kb_search(
    q: str = Query(..., min_length=1, max_length=100, description="检索关键词"),
    limit: int = Query(8, ge=1, le=20),
    user: User = Depends(get_current_user),
):
    """检索结果 = 内置操作指引（策展层）+ 用户文档，来源明确区分。"""
    data = search(q, limit)
    data["builtin"] = knowledge_playbooks.search_playbooks(q)
    data["playbook_count"] = knowledge_playbooks.list_playbooks()["count"]
    return data


@router.get("/playbooks")
async def kb_playbooks(user: User = Depends(get_current_user)):
    """内置操作指引清单：人工策展的方法论蒸馏，只描述方法与边界。"""
    return knowledge_playbooks.list_playbooks()


@router.post("/rebuild")
async def kb_rebuild(user: User = Depends(get_current_user)):
    """手动重建索引（新增文件后调用）。"""
    return {"success": True, **rebuild()}
