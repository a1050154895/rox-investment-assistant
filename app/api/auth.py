"""认证 API — 注册 / 登录 / 当前用户 / 找回密码 / 修改密码 / 邮箱绑定与验证。"""
import re
from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import (
    clear_auth_cookie,
    create_token,
    get_current_user,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from app.core.config import settings
from app.core.limiter import limiter
from app.db import get_db
from app.models import User, utcnow
from app.services import mailer
from app.services.auth_tokens import (
    RESET_TOKEN_TTL_MINUTES,
    VERIFY_TOKEN_TTL_MINUTES,
    consume_token,
    invalidate_user_tokens,
    issue_token,
    last_issued_at,
)

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RESEND_THROTTLE_SECONDS = 60

_PURPOSE_RESET = "reset_password"
_PURPOSE_VERIFY = "verify_email"


class RegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="用户名，3-30 字符")
    password: str = Field(..., min_length=6, max_length=64, description="密码，至少 6 位")
    email: str | None = Field(None, max_length=120, description="邮箱，可选；绑定后需在设置中验证才能用于找回密码")


class LoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    password: str = Field(..., min_length=1, max_length=64)


class ForgotPasswordIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)


class ResetPasswordIn(BaseModel):
    token: str = Field(..., min_length=16, max_length=200)
    new_password: str = Field(..., min_length=6, max_length=64)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)


class BindEmailIn(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)


class VerifyEmailIn(BaseModel):
    token: str = Field(..., min_length=16, max_length=200)


@router.post("/register")
@limiter.limit("10/minute")
async def register(request: Request, data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    """注册新用户，返回 JWT token。邮箱为可选项，绑定后需验证才可用于找回密码。"""
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="用户名不能为空")
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在，请直接登录")
    user = User(username=username, password_hash=hash_password(data.password))
    if data.email and data.email.strip():
        email = data.email.strip().lower()
        if not _EMAIL_RE.match(email):
            raise HTTPException(status_code=422, detail="邮箱格式不正确")
        user.email = email
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id)
    set_auth_cookie(response, token)
    return {"success": True, "token": token, "user": user.to_dict()}


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, data: LoginIn, db: Session = Depends(get_db)):
    """登录，返回 JWT token。"""
    user = db.query(User).filter(User.username == data.username.strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user.id)
    set_auth_cookie(response, token)
    return {"success": True, "token": token, "user": user.to_dict()}


@router.post("/logout")
async def logout(response: Response):
    """清除登录 Cookie。"""
    clear_auth_cookie(response)
    return {"success": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """当前登录用户信息。"""
    return {"user": user.to_dict()}


@router.get("/recovery-status")
async def recovery_status():
    """邮件找回能力状态；未配置 SMTP 时前端如实提示，不提供假入口。"""
    return {"email_configured": mailer.email_configured()}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordIn, db: Session = Depends(get_db)):
    """请求密码重置链接。

    为防用户名枚举：用户不存在、未绑定邮箱、邮箱未验证、处于重发节流期，
    一律返回与成功时完全相同的响应；仅 SMTP 未配置时统一返回 503。
    """
    user = db.query(User).filter(User.username == data.username.strip()).first()
    if user and user.email and user.email_verified_at is not None:
        last = last_issued_at(db, user.id, _PURPOSE_RESET)
        throttled = last is not None and (utcnow() - last).total_seconds() < _RESEND_THROTTLE_SECONDS
        if not throttled:
            raw = issue_token(db, user.id, _PURPOSE_RESET, RESET_TOKEN_TTL_MINUTES)
            link = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={raw}"
            html = _email_html(
                "ROX 密码重置",
                "我们收到了您的找回密码请求。请点击下面的链接设置新密码：",
                link,
                f"链接 30 分钟内有效。如果您没有发起找回密码，请忽略本邮件，您的密码不会被修改。",
            )
            try:
                mailer.send_email(user.email, "ROX 密码重置", html)
            except Exception:
                db.rollback()
                raise HTTPException(status_code=503, detail="邮件服务暂不可用，请稍后再试")
            db.commit()
    return {
        "success": True,
        "message": "如果该用户名绑定了已验证邮箱，重置链接已发送，请查收邮件（注意垃圾箱）。60 秒内重复请求不会重复发送。",
    }


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(request: Request, data: ResetPasswordIn, db: Session = Depends(get_db)):
    """凭邮件令牌设置新密码；成功后作废该用户其余重置令牌并使旧登录态失效。"""
    user_id = consume_token(db, data.token, _PURPOSE_RESET)
    if user_id is None:
        raise HTTPException(status_code=400, detail="重置链接无效或已过期，请重新发起找回密码")
    user = db.get(User, user_id)
    if user is None:
        db.rollback()
        raise HTTPException(status_code=400, detail="重置链接无效或已过期，请重新发起找回密码")
    user.password_hash = hash_password(data.new_password)
    user.password_changed_at = utcnow()
    invalidate_user_tokens(db, user.id, _PURPOSE_RESET)
    db.commit()
    return {"success": True, "message": "密码已重置，请使用新密码登录。"}


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    data: ChangePasswordIn,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """登录态下修改密码；旧密码必须正确，成功后重签发当前会话令牌。"""
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    changed_at = utcnow()
    user.password_hash = hash_password(data.new_password)
    user.password_changed_at = changed_at
    db.commit()
    # 重签发的当前会话令牌：iat 精确等于变更时刻（见 create_token 说明）
    token = create_token(user.id, iat_epoch=changed_at.replace(tzinfo=timezone.utc).timestamp())
    set_auth_cookie(response, token)
    return {"success": True, "message": "密码已修改，其他设备需要重新登录。", "token": token}


@router.post("/email/bind")
@limiter.limit("3/minute")
async def bind_email(
    request: Request,
    data: BindEmailIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """绑定或更换邮箱；换绑后验证状态清零，需重新验证。同一验证邮箱不可归属多个账号。"""
    email = data.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="邮箱格式不正确")
    if user.email == email and user.email_verified_at is not None:
        return {"success": True, "message": "该邮箱已验证，无需重复绑定。", "email": user.email, "email_verified": True}
    taken = (
        db.query(User)
        .filter(User.email == email, User.id != user.id, User.email_verified_at.isnot(None))
        .first()
    )
    if taken:
        raise HTTPException(status_code=409, detail="该邮箱已被其他账号验证使用")
    last = last_issued_at(db, user.id, _PURPOSE_VERIFY)
    if last is not None and (utcnow() - last).total_seconds() < _RESEND_THROTTLE_SECONDS:
        raise HTTPException(status_code=429, detail="验证邮件发送过于频繁，请 60 秒后再试")
    user.email = email
    user.email_verified_at = None
    raw = issue_token(db, user.id, _PURPOSE_VERIFY, VERIFY_TOKEN_TTL_MINUTES)
    link = f"{settings.APP_BASE_URL.rstrip('/')}/verify-email?token={raw}"
    html = _email_html(
        "ROX 邮箱验证",
        "请点击下面的链接完成邮箱验证，验证后即可使用邮箱找回密码：",
        link,
        "链接 24 小时内有效。如果您没有绑定过该邮箱，请忽略本邮件。",
    )
    try:
        mailer.send_email(email, "ROX 邮箱验证", html)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="邮件服务暂不可用，请稍后再试")
    db.commit()
    return {
        "success": True,
        "message": f"验证邮件已发送至 {email}，请查收并点击验证链接（注意垃圾箱）。",
        "email": user.email,
        "email_verified": False,
    }


@router.post("/email/verify")
@limiter.limit("10/minute")
async def verify_email(request: Request, data: VerifyEmailIn, db: Session = Depends(get_db)):
    """凭邮件令牌验证绑定邮箱。"""
    user_id = consume_token(db, data.token, _PURPOSE_VERIFY)
    if user_id is None:
        raise HTTPException(status_code=400, detail="验证链接无效或已过期，请在设置中重新发送验证邮件")
    user = db.get(User, user_id)
    if user is None or not user.email:
        db.rollback()
        raise HTTPException(status_code=400, detail="验证链接无效或已过期，请在设置中重新发送验证邮件")
    conflict = (
        db.query(User)
        .filter(User.email == user.email, User.id != user.id, User.email_verified_at.isnot(None))
        .first()
    )
    if conflict:
        db.rollback()
        raise HTTPException(status_code=409, detail="该邮箱已被其他账号验证使用，请在设置中更换邮箱")
    user.email_verified_at = utcnow()
    db.commit()
    return {"success": True, "message": "邮箱验证成功，找回密码功能已可用。"}


def _email_html(title: str, lead: str, link: str, foot: str) -> str:
    """简单内联样式的邮件正文，不依赖外部资源。"""
    return f"""\
<div style="font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1a1a1a;">
  <h2 style="font-size:18px;margin:0 0 16px;">{title}</h2>
  <p style="font-size:14px;line-height:1.7;margin:0 0 16px;">{lead}</p>
  <p style="margin:0 0 16px;">
    <a href="{link}" style="display:inline-block;background:#b3492f;color:#ffffff;text-decoration:none;padding:10px 20px;border-radius:6px;font-size:14px;">打开链接</a>
  </p>
  <p style="font-size:12px;line-height:1.6;color:#666;word-break:break-all;margin:0 0 8px;">如按钮无效，请复制以下地址到浏览器打开：<br>{link}</p>
  <p style="font-size:12px;line-height:1.6;color:#666;margin:0;">{foot}</p>
</div>"""
