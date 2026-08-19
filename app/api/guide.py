"""使用教程 API — 返回新手引导步骤与功能说明。"""
from fastapi import APIRouter

from app.services.guide import FEATURES, ONBOARDING_STEPS

router = APIRouter()


@router.get("/")
async def guide():
    return {
        "onboarding_steps": ONBOARDING_STEPS,
        "features": FEATURES,
    }
