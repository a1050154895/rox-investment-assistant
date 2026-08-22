"""BYOK 密钥加密存储。

用 SECRET_KEY 派生 Fernet 密钥，用户自带的 AI API Key 以
"enc:<token>" 形式落库，明文不进数据库、不进日志、不回传前端。
旧数据中的明文 Key 仍可读（读取时识别），下次保存时自动升级为密文。
"""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.auth import SECRET_KEY

logger = logging.getLogger(__name__)

_PREFIX = "enc:"

_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()))


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    if plaintext.startswith(_PREFIX):
        return plaintext  # 已是密文，避免二次加密
    return _PREFIX + _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(stored: str) -> str:
    if not stored:
        return ""
    if not stored.startswith(_PREFIX):
        return stored  # 历史明文，直接可用（保存时再升级）
    try:
        return _fernet.decrypt(stored[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        logger.warning("密钥解密失败（SECRET_KEY 可能已更换），视为未配置")
        return ""


def mask_secret(stored: str) -> str | None:
    """脱敏展示：仅用于确认是否配置过，绝不回传明文。"""
    plaintext = decrypt_secret(stored)
    if not plaintext:
        return None
    if len(plaintext) <= 8:
        return "****"
    return f"{plaintext[:4]}****{plaintext[-4:]}"
