"""账号扩展属性（邮箱/验证时间/密码变更时间）的键值存取。

设计说明：这些低频写入的账号属性走既有 Setting 键值表（与 BYOK 密钥同模式），
而不是 users 表新列——避免运行时 ALTER TABLE 迁移（曾在 PostgreSQL 上因方言
差异导致部署崩溃），也与"users 表保持最小核心字段"的现状一致。

约定：
- email 统一小写存储；
- email_verified_at 有值即视为已验证；
- password_changed_at 有值时，早于该时刻签发的 JWT 一律失效（见 core/auth.py）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Setting, utcnow

KEY_EMAIL = "account.email"
KEY_EMAIL_VERIFIED_AT = "account.email_verified_at"
KEY_PASSWORD_CHANGED_AT = "account.password_changed_at"


def get_value(db: Session, user_id: int, key: str) -> str | None:
    row = (
        db.query(Setting)
        .filter(Setting.user_id == user_id, Setting.key == key)
        .first()
    )
    return row.value if row else None


def set_value(db: Session, user_id: int, key: str, value: str) -> None:
    row = (
        db.query(Setting)
        .filter(Setting.user_id == user_id, Setting.key == key)
        .first()
    )
    if row:
        row.value = value
    else:
        db.add(Setting(user_id=user_id, key=key, value=value))


def delete_value(db: Session, user_id: int, key: str) -> None:
    db.query(Setting).filter(Setting.user_id == user_id, Setting.key == key).delete()


def get_email(db: Session, user_id: int) -> str | None:
    return get_value(db, user_id, KEY_EMAIL)


def get_email_verified_at(db: Session, user_id: int) -> datetime | None:
    raw = get_value(db, user_id, KEY_EMAIL_VERIFIED_AT)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def set_email(db: Session, user_id: int, email: str) -> None:
    set_value(db, user_id, KEY_EMAIL, email)
    delete_value(db, user_id, KEY_EMAIL_VERIFIED_AT)  # 换绑后必须重新验证


def mark_email_verified(db: Session, user_id: int) -> None:
    set_value(db, user_id, KEY_EMAIL_VERIFIED_AT, utcnow().isoformat())


def mark_password_changed(db: Session, user_id: int) -> None:
    set_value(db, user_id, KEY_PASSWORD_CHANGED_AT, utcnow().isoformat())


def get_password_changed_at(db: Session, user_id: int) -> datetime | None:
    raw = get_value(db, user_id, KEY_PASSWORD_CHANGED_AT)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def find_user_id_by_verified_email(db: Session, email: str) -> int | None:
    """按已验证邮箱反查用户；邮箱唯一性以「已验证」为准。"""
    rows = (
        db.query(Setting)
        .filter(Setting.key == KEY_EMAIL, Setting.value == email)
        .all()
    )
    for row in rows:
        if get_email_verified_at(db, row.user_id) is not None:
            return row.user_id
    return None


def email_verified_by_other(db: Session, email: str, exclude_user_id: int) -> bool:
    """该邮箱是否已被其他账号验证。"""
    owner = find_user_id_by_verified_email(db, email)
    return owner is not None and owner != exclude_user_id


def account_public_fields(db: Session, user_id: int) -> dict:
    """登录/注册/me 响应中的邮箱字段，保持与原 User.to_dict 相同的键。"""
    email = get_email(db, user_id)
    return {
        "email": email,
        "email_verified": get_email_verified_at(db, user_id) is not None,
    }
