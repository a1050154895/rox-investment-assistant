"""用户反馈 API — 免费公测期需求收集主渠道。

反馈仅存本地数据库；配置了 FEEDBACK_EMAIL 且 SMTP 可用时，额外转发一封邮件
（尽力而为，失败不影响反馈保存）。
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db import get_db
from app.models import Feedback, User
from app.services import mailer

router = APIRouter()


class FeedbackIn(BaseModel):
    content: str = Field(..., min_length=5, max_length=2000, description="反馈内容")
    contact: str = Field("", max_length=100, description="联系方式（可选，便于回访）")
    page: str = Field("", max_length=100, description="反馈来源页面")


@router.post("")
@limiter.limit("3/minute")
async def submit_feedback(request: Request, data: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="反馈内容不能为空")
    row = Feedback(user_id=user.id, content=content, contact=data.contact.strip()[:100], page=data.page.strip()[:100])
    db.add(row)
    db.commit()
    db.refresh(row)

    forwarded = False
    if settings.FEEDBACK_EMAIL and mailer.email_configured():
        try:
            html = f"<p><b>用户</b>：{user.username}（{data.contact or '未留联系方式'}）</p><p><b>页面</b>：{data.page or '-'}</p><p>{content}</p>"
            mailer.send_email(settings.FEEDBACK_EMAIL, "ROX 用户反馈", html.replace("\n", "<br>"))
            forwarded = True
        except Exception:  # noqa: BLE001 — 邮件转发失败不影响反馈保存
            forwarded = False

    return {
        "success": True,
        "message": "反馈已收到，感谢！免费公测期的每一条反馈都会被认真对待。",
        "forwarded": forwarded,
        "id": row.id,
    }
