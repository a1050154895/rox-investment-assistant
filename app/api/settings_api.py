"""设置 API — 用户设置（数据库持久化，按用户隔离）+ 会员信息。

安全约定：
- AI API Key 允许保存，但任何 GET 响应均不返回明文，仅返回是否已配置。
- 会员信息基于用户真实 plan 计算，不再返回硬编码假数据。
"""
import json
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import Setting, User

router = APIRouter()

# 可持久化字段及默认值（不包含明文 key 的回读）
DEFAULT_SETTINGS = {
    "ai_provider": "deepseek",
    "ai_api_url": "https://api.deepseek.com",
    "ai_model": "deepseek-chat",
    "theme": "dark",
    "compact_mode": "false",
    "chart_style": "candlestick",
    "default_period": "daily",
    "data_source": "akshare",
}

# 只允许保存的键（白名单，防注入任意设置）
ALLOWED_KEYS = set(DEFAULT_SETTINGS.keys()) | {"ai_api_key"}

# 套餐定义（价格与权益为公开展示信息）
PLANS = [
    {"name": "基础版", "price": 0, "period": "永久", "features": ["每日API 100次", "基础行情", "简单图表"]},
    {"name": "专业版", "price": 99, "period": "月", "features": ["每日API 10,000次", "实时行情", "高级图表", "主力资金分析", "框架评分"]},
    {"name": "尊享版", "price": 299, "period": "月", "features": ["无限API", "全功能", "AI深度分析", "专属策略", "优先支持"]},
]


class SettingsUpdate(BaseModel):
    ai_provider: str | None = Field(None, max_length=30)
    ai_api_url: str | None = Field(None, max_length=300)
    ai_model: str | None = Field(None, max_length=100)
    ai_api_key: str | None = Field(None, max_length=300)
    theme: str | None = Field(None, max_length=20)
    compact_mode: bool | None = None
    chart_style: str | None = Field(None, max_length=20)
    default_period: str | None = Field(None, max_length=20)
    data_source: str | None = Field(None, max_length=20)


def _get_all(db: Session, user_id: int) -> dict:
    rows = db.query(Setting).filter(Setting.user_id == user_id).all()
    stored = {r.key: r.value for r in rows}
    out = dict(DEFAULT_SETTINGS)
    for k, v in stored.items():
        if k == "ai_api_key":
            continue  # 永不回传明文密钥
        if k == "compact_mode":
            out[k] = v == "true"
        else:
            out[k] = v
    return out


@router.get("/")
async def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取当前用户设置（AI Key 不回传，仅标记是否已配置）。"""
    settings = _get_all(db, user.id)
    key_configured = bool(os.getenv("AI_API_KEY", "").strip())
    if not key_configured:
        row = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == "ai_api_key").first()
        key_configured = bool(row and row.value)
    return {**settings, "ai_key_configured": key_configured}


@router.put("/")
async def update_settings(
    update: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存当前用户设置。"""
    data = update.model_dump(exclude_none=True)
    for k, v in data.items():
        if k not in ALLOWED_KEYS:
            continue
        stored_value = "true" if k == "compact_mode" and isinstance(v, bool) else str(v)
        row = db.query(Setting).filter(Setting.user_id == user.id, Setting.key == k).first()
        if row:
            row.value = stored_value
        else:
            db.add(Setting(user_id=user.id, key=k, value=stored_value))
    db.commit()
    return {"success": True, "settings": _get_all(db, user.id)}


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
