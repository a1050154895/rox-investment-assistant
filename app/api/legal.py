"""法律与合规文档 API（公开，登录前后均可读）。"""
from fastapi import APIRouter, HTTPException

from app.services.legal_docs import get_legal_doc, get_legal_docs

router = APIRouter()


@router.get("")
async def legal_index():
    """法律文档清单：用户协议 / 隐私政策 / 风险揭示。"""
    return get_legal_docs()


@router.get("/{doc_id}")
async def legal_detail(doc_id: str):
    doc = get_legal_doc(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc
