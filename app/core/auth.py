"""认证核心：密码哈希（PBKDF2，标准库）与 JWT 签发/校验。

生产环境必须设置 SECRET_KEY 环境变量；未设置时使用随机密钥（进程重启后旧 token 失效）。
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

_env_key = os.getenv("SECRET_KEY", "").strip()
SECRET_KEY = _env_key or secrets.token_hex(32)
KEY_SOURCE = "env" if _env_key else "random"  # random = 重启后 JWT 全部失效
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24 * 7  # 7 天

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


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：解析 Bearer token 并返回当前用户；无效则 401。"""
    if creds is None:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except Exception:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user
