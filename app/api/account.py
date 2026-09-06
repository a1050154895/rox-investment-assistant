"""账号注销 — 数据删除权（隐私政策承诺的最重要用户权利）。

注销将不可逆删除该用户全部账号数据：速记、异动事件、自选、预警、持仓、
纪律档案、认证令牌、设置（含邮箱与 BYOK 密钥）、反馈、研究事件、研究卡、
决策日志（含决策上下文），最后删除用户本身。
需要密码二次确认；操作成功后清除登录 Cookie。
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import clear_auth_cookie, get_current_user, verify_password
from app.core.limiter import limiter
from app.db import get_db
from app.models import (
    Alert, AnomalyEvent, AuthToken, DecisionContext, DisciplineProfile,
    Feedback, JournalEntry, Position, QuickNote, ResearchCard, ResearchEvent,
    Setting, User, Watchlist,
)

router = APIRouter()

# 删除顺序：先明细后主体；DecisionContext 挂在决策日志上，需最先按日志范围删除
# （DecisionContext 无 user_id 列，见函数内单独处理）
_DELETE_ORDER = (
    ResearchEvent, ResearchCard, JournalEntry, QuickNote,
    AnomalyEvent, Watchlist, Alert, Position, DisciplineProfile, AuthToken,
    Setting, Feedback,
)


class DeleteAccountIn(BaseModel):
    password: str = Field(..., min_length=1, max_length=64, description="当前密码，二次确认")


@router.delete("")
@limiter.limit("3/minute")
async def delete_account(
    request: Request,
    data: DeleteAccountIn,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=403, detail="密码不正确，账号未注销")

    journal_ids = [row.id for row in db.query(JournalEntry.id).filter(JournalEntry.user_id == user.id)]
    if journal_ids:
        db.query(DecisionContext).filter(DecisionContext.journal_id.in_(journal_ids)).delete(synchronize_session=False)

    deleted = {}
    for model in _DELETE_ORDER:
        count = db.query(model).filter(model.user_id == user.id).delete(synchronize_session=False)
        if count:
            deleted[model.__tablename__] = count
    db.delete(user)
    db.commit()

    clear_auth_cookie(response)
    return {
        "success": True,
        "deleted": deleted,
        "message": "账号已注销，全部数据已删除。感谢你使用 ROX，期待未来再见。",
    }
