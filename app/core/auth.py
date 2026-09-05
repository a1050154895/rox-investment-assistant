"""认证核心：密码哈希（PBKDF2，标准库）与 JWT 签发/校验。

生产环境必须设置 SECRET_KEY 环境变量；未设置时使用随机密钥（进程重启后旧 token 失效）。
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import User

_env_key = os.getenv("SECRET_KEY", "").strip()
SECRET_KEY = _env_key or secrets.token_hex(32)
KEY_SOURCE = "env" if _env_key else "random"  # random = 重启后 JWT 全部失效
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24 * 7  # 7 天
COOKIE_NAME = "rox_token"

_bearer = HTTPBearer(auto_error=False)

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS).hex()
        return hmac.compare_digest(check, digest)
    except Exception:
        return False


def create_token(user_id: int, iat_epoch: float | None = None) -> str:
    """签发 JWT。

    iat_epoch 可显式指定为 Unix 秒（浮点）。密码变更后重签会话令牌时必须用它把 iat
    精确设为变更时刻：早于变更时刻会被 get_current_user 的失效校验拒绝，而明显晚于
    当前时间又会被 PyJWT 的未来 iat 校验（ImmatureSignatureError）拒绝。
    """
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        "iat": iat_epoch if iat_epoch is not None else datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def set_auth_cookie(response: Response, token: str) -> None:
    """把 JWT 写入 HttpOnly Cookie（同源 SPA 自动携带，降低 XSS 暴露面）。"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=TOKEN_TTL_HOURS * 3600,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：优先从 HttpOnly Cookie 读取 JWT，兼容 Bearer header；无效则 401。"""
    token = request.cookies.get(COOKIE_NAME) or (creds.credentials if creds else None)
    if not token:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except Exception:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if _issued_before_password_change(payload, user):
        raise HTTPException(status_code=401, detail="密码已变更，请重新登录")
    return user


def _issued_before_password_change(payload: dict, user: User) -> bool:
    """密码变更/重置后，此前签发的 JWT 一律失效：iat 严格早于变更时刻即拒绝。

    重签发的令牌由调用方把 iat 设为变更时刻之后，因此不会被自身校验拒绝。
    """
    iat = payload.get("iat")
    changed_at = user.password_changed_at
    if iat is None or changed_at is None:
        return False
    iat_epoch = iat.timestamp() if isinstance(iat, datetime) else float(iat)
    changed_epoch = changed_at.replace(tzinfo=timezone.utc).timestamp()
    return iat_epoch < changed_epoch
