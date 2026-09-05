"""一次性认证令牌：找回密码 / 邮箱验证。

令牌明文（token_urlsafe(32)）只出现在邮件链接里，库中仅存 SHA-256 哈希；
单次使用（消费即置 used_at），签发时作废同用户同用途的旧令牌并顺带清理过期行。
所有函数不主动 commit，事务边界由调用方控制（例如发信失败时整体回滚）。
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AuthToken, utcnow

RESET_TOKEN_TTL_MINUTES = 30
VERIFY_TOKEN_TTL_MINUTES = 24 * 60

_PURPOSE_RESET = "reset_password"
_PURPOSE_VERIFY = "verify_email"


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_token(db: Session, user_id: int, purpose: str, ttl_minutes: int) -> str:
    """签发令牌，返回明文。同用户同用途的旧令牌（含未使用的）全部作废。"""
    db.query(AuthToken).filter(AuthToken.expires_at < utcnow()).delete()
    db.query(AuthToken).filter(AuthToken.user_id == user_id, AuthToken.purpose == purpose).delete()
    raw = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=_hash(raw),
            expires_at=utcnow() + timedelta(minutes=ttl_minutes),
        )
    )
    return raw


def consume_token(db: Session, raw: str, purpose: str) -> int | None:
    """校验并消费令牌（置 used_at，不 commit）；有效返回 user_id，无效/过期返回 None。"""
    if not raw:
        return None
    row = (
        db.query(AuthToken)
        .filter(AuthToken.token_hash == _hash(raw.strip()), AuthToken.purpose == purpose, AuthToken.used_at.is_(None))
        .first()
    )
    if row is None or row.expires_at < utcnow():
        return None
    row.used_at = utcnow()
    return row.user_id


def invalidate_user_tokens(db: Session, user_id: int, purpose: str) -> None:
    """作废该用户指定用途的所有未使用令牌（不 commit）。"""
    db.query(AuthToken).filter(
        AuthToken.user_id == user_id,
        AuthToken.purpose == purpose,
        AuthToken.used_at.is_(None),
    ).update({"used_at": utcnow()})


def last_issued_at(db: Session, user_id: int, purpose: str) -> datetime | None:
    """该用户该用途最近一次签发时间（用于重发节流）。"""
    row = (
        db.query(AuthToken)
        .filter(AuthToken.user_id == user_id, AuthToken.purpose == purpose)
        .order_by(AuthToken.created_at.desc())
        .first()
    )
    return row.created_at if row else None
