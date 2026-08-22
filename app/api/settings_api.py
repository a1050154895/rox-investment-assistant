"""设置 API — 用户设置（数据库持久化，按用户隔离）+ 会员信息。

安全约定：
- AI 三层模式：ai_mode = off（不使用 AI）/ platform（平台 AI）/ byok（自带模型）。
- BYOK 的 API Key 用 SECRET_KEY 派生密钥加密落库（enc: 前缀），任何 GET 响应
  均不返回明文，仅返回脱敏尾部与是否已配置；支持随时删除/轮换。
- 会员信息基于用户真实 plan 计算，不返回硬编码假数据。
"""
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.db import get_db
from app.models import Setting, User

router = APIRouter()

AI_MODES = {"off": "不使用 AI", "platform": "使用平台 AI", "byok": "使用我的模型（BYOK）"}

# 可持久化字段及默认值（不包含明文 key 的回读）
DEFAULT_SETTINGS = {
    "ai_mode": "platform",
    "ai_provider": "deepseek",
    "ai_api_url": "https://api.deepseek.com",
    "ai_model": "deepseek-chat",
    "ai_fallback_url": "",
    "ai_fallback_model": "",
    "ai_send_card_content": "false",
    "theme": "dark",
    "compact_mode": "false",
    "chart_style": "candlestick",
    "default_period": "daily",
    "data_source": "akshare",
}

# 只允许保存的键（白名单，防注入任意设置）
ALLOWED_KEYS = set(DEFAULT_SETTINGS.keys()) | {"ai_api_key", "ai_fallback_key"}

# 套餐定义（价格与权益为公开展示信息）
PLANS = [
    {"name": "基础版", "price": 0, "period": "永久", "features": ["每日API 100次", "基础行情", "简单图表"]},
    {"name": "专业版", "price": 99, "period": "月", "features": ["每日API 10,000次", "实时行情", "高级图表", "主力资金分析", "框架评分"]},
    {"name": "尊享版", "price": 299, "period": "月", "features": ["无限API", "全功能", "AI深度分析", "专属策略", "优先支持"]},
]


class SettingsUpdate(BaseModel):
    ai_mode: str | None = Field(None, max_length=20)
    ai_provider: str | None = Field(None, max_length=30)
    ai_api_url: str | None = Field(None, max_length=300)
    ai_api_key: str | None = Field(None, max_length=300)
    ai_model: str | None = Field(None, max_length=100)
    ai_fallback_url: str | None = Field(None, max_length=300)
    ai_fallback_key: str | None = Field(None, max_length=300)
    ai_fallback_model: str | None = Field(None, max_length=100)
    ai_send_card_content: bool | None = None
    theme: str | None = Field(None, max_length=20)
    compact_mode: bool | None = None
    chart_style: str | None = Field(None, max_length=20)
    default_period: str | None = Field(None, max_length=20)
    data_source: str | None = Field(None, max_length=20)

    @field_validator("ai_mode")
    @classmethod
    def _valid_mode(cls, value: str | None) -> str | None:
        if value is not None and value not in AI_MODES:
            raise ValueError(f"ai_mode 必须是 {sorted(AI_MODES)} 之一")
        return value


def _get_stored(db: Session, user_id: int) -> dict:
    rows = db.query(Setting).filter(Setting.user_id == user_id).all()
    return {r.key: r.value for r in rows}


def _get_all(db: Session, user_id: int) -> dict:
    stored = _get_stored(db, user_id)
    out = dict(DEFAULT_SETTINGS)
    for k, v in stored.items():
        if k in ("ai_api_key", "ai_fallback_key"):
            continue  # 永不回传密钥
        if k in ("compact_mode", "ai_send_card_content"):
            out[k] = v == "true"
        else:
            out[k] = v
    return out


@router.get("/")
async def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取当前用户设置（AI Key 不回传，仅返回脱敏提示与是否已配置）。"""
    settings = _get_all(db, user.id)
    stored = _get_stored(db, user.id)
    byok_key = decrypt_secret(stored.get("ai_api_key", ""))
    platform_key = bool(os.getenv("AI_API_KEY", "").strip())
    return {
        **settings,
        "ai_mode_label": AI_MODES.get(settings["ai_mode"], settings["ai_mode"]),
        "ai_key_masked": mask_secret(stored.get("ai_api_key", "")),
        "ai_fallback_configured": bool(decrypt_secret(stored.get("ai_fallback_key", ""))),
        "ai_key_configured": bool(byok_key or platform_key),
        "platform_ai_available": platform_key,
        "ai_modes": [{"value": k, "label": v} for k, v in AI_MODES.items()],
    }


@router.put("/")
async def update_settings(
    update: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存当前用户设置；BYOK Key 加密后落库。传空字符串 Key 视为删除。"""
    data = update.model_dump(exclude_none=True)
    for k, v in data.items():
        if k not in ALLOWED_KEYS:
            continue
        if k in ("compact_mode", "ai_send_card_content"):
            stored_value = "true" if isinstance(v, bool) and v else "false"
        elif k in ("ai_api_key", "ai_fallback_key"):
            stored_value = encrypt_secret(str(v).strip()) if str(v).strip() else ""
        else:
            stored_value = str(v)
        row = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == k).first()
        if row:
            row.value = stored_value
        else:
            db.add(Setting(user_id=user.id, key=k, value=stored_value))
    db.commit()
    return {"success": True, "settings": await get_settings(user, db)}


@router.delete("/ai-key")
async def delete_ai_key(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除 BYOK 密钥（立即生效，不可恢复）。"""
    row = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == "ai_api_key").first()
    if row:
        row.value = ""
        db.commit()
    return {"success": True, "message": "BYOK 密钥已删除"}


@router.get("/membership")
async def get_membership(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """会员信息 — 基于用户真实 plan 计算，不返回假数据。"""
    plan = user.plan if user.plan in {p["name"] for p in PLANS} else "基础版"
    return {
        "plan": plan,
        "status": "active" if plan != "基础版" else "free",
        "days_left": None,  # 付费订阅上线前不展示虚构天数
        "api_used": None,
        "api_limit": None,
        "features_unlocked": 0,
        "features_total": len(PLANS[0]["features"]),
        "plans": PLANS,
        "note": "付费套餐正在接入，当前为基础版；后续版本将开放支付与权益激活。",
    }
