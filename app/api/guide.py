"""使用教程 API — 返回新手引导步骤与功能说明。"""
from fastapi import APIRouter

from app.services.guide import FAQ, FEATURES, GLOSSARY, ONBOARDING_STEPS, SHORTCUTS

router = APIRouter()


@router.get("/")
async def guide():
    return {
        "onboarding_steps": ONBOARDING_STEPS,
        "features": FEATURES,
        "faq": FAQ,
        "glossary": GLOSSARY,
        "shortcuts": SHORTCUTS,
    }
