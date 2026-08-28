"""快速速记 API — 盘中灵感、事件快记，可关联研究卡。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import QuickNote, ResearchCard, User

router = APIRouter()


class NoteIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    code: str = Field("", max_length=10)
    stock: str = Field("", max_length=30)
    tag: str = Field("", max_length=20)
    research_card_id: int | None = None
    pinned: bool = False


class NoteUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    code: str = Field("", max_length=10)
    stock: str = Field("", max_length=30)
    tag: str = Field("", max_length=20)
    research_card_id: int | None = None
    pinned: bool = False


@router.get("/")
async def list_notes(
    tag: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户的速记，置顶优先，按时间倒序。"""
    q = db.query(QuickNote).filter(QuickNote.user_id == user.id)
    if tag:
        q = q.filter(QuickNote.tag == tag)
    notes = q.order_by(QuickNote.pinned.desc(), QuickNote.created_at.desc()).all()
    return [n.to_dict() for n in notes]


@router.post("/")
async def create_note(
    data: NoteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建一条速记。"""
    if data.research_card_id is not None:
        card = db.query(ResearchCard).filter(
            ResearchCard.id == data.research_card_id,
            ResearchCard.user_id == user.id,
        ).first()
        if not card:
            raise HTTPException(status_code=404, detail="研究卡不存在")

    note = QuickNote(
        user_id=user.id,
        content=data.content,
        code=data.code,
        stock=data.stock,
        tag=data.tag,
        research_card_id=data.research_card_id,
        pinned=data.pinned,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note.to_dict()


@router.put("/{note_id}")
async def update_note(
    note_id: int,
    data: NoteUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新一条速记。"""
    note = db.query(QuickNote).filter(
        QuickNote.id == note_id,
        QuickNote.user_id == user.id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="速记不存在")

    if data.research_card_id is not None:
        card = db.query(ResearchCard).filter(
            ResearchCard.id == data.research_card_id,
            ResearchCard.user_id == user.id,
        ).first()
        if not card:
            raise HTTPException(status_code=404, detail="研究卡不存在")

    note.content = data.content
    note.code = data.code
    note.stock = data.stock
    note.tag = data.tag
    note.research_card_id = data.research_card_id
    note.pinned = data.pinned
    db.commit()
    db.refresh(note)
    return note.to_dict()


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除一条速记。"""
    note = db.query(QuickNote).filter(
        QuickNote.id == note_id,
        QuickNote.user_id == user.id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="速记不存在")

    db.delete(note)
    db.commit()
    return {"ok": True}


@router.post("/{note_id}/toggle-pin")
async def toggle_pin(
    note_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换置顶状态。"""
    note = db.query(QuickNote).filter(
        QuickNote.id == note_id,
        QuickNote.user_id == user.id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="速记不存在")

    note.pinned = not note.pinned
    db.commit()
    db.refresh(note)
    return note.to_dict()


@router.get("/tags")
async def list_tags(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户使用过的所有标签。"""
    notes = db.query(QuickNote).filter(
        QuickNote.user_id == user.id,
        QuickNote.tag != "",
    ).all()
    tags = sorted(set(n.tag for n in notes if n.tag))
    return tags
