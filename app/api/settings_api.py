"""设置 API — 用户设置、会员信息"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# 内存存储
_settings = {
    "ai_provider": "deepseek",
    "ai_api_url": "https://api.deepseek.com",
    "ai_model": "deepseek-chat",
    "theme": "dark",
    "compact_mode": False,
    "chart_style": "candlestick",
    "default_period": "daily",
    "data_source": "akshare",
}

_membership = {
    "plan": "专业版",
    "status": "active",
    "days_left": 23,
    "api_used": 342,
    "api_limit": 10000,
    "features_unlocked": 12,
    "features_total": 15,
    "plans": [
        {"name": "基础版", "price": 0, "period": "永久", "features": ["每日API 100次", "基础行情", "简单图表"]},
        {"name": "专业版", "price": 99, "period": "月", "features": ["每日API 10,000次", "实时行情", "高级图表", "主力资金分析", "框架评分"]},
        {"name": "尊享版", "price": 299, "period": "月", "features": ["无限API", "全功能", "AI深度分析", "专属策略", "优先支持"]},
    ]
}


class SettingsUpdate(BaseModel):
    ai_provider: str | None = None
    ai_api_url: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    theme: str | None = None
    compact_mode: bool | None = None
    chart_style: str | None = None
    default_period: str | None = None
    data_source: str | None = None


@router.get("/")
async def get_settings():
    return _settings


@router.put("/")
async def update_settings(update: SettingsUpdate):
    for k, v in update.model_dump(exclude_none=True).items():
        if k == "ai_api_key":
            continue  # 不返回密钥
        _settings[k] = v
    return {"success": True, "settings": _settings}


@router.get("/membership")
async def get_membership():
    return _membership
