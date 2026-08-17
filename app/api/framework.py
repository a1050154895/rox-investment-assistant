"""认知框架 API — 方法论、策略库、知识库

方法论与策略/知识数据统一从 app.services.methodology 单一事实源读取，
避免同一份方法论在多处硬编码、产生口径漂移。

思想来源登记见 docs/strategy_origins.md
"""
from fastapi import APIRouter, Query

from app.services.methodology import (
    KNOWLEDGE_ARTICLES,
    KNOWLEDGE_CATEGORIES,
    METHODOLOGY_LAYERS,
    STRATEGIES,
)

router = APIRouter()


@router.get("/methodology")
async def methodology():
    """五层逻辑链方法论（单一事实源 + RIA-TV++ 蒸馏元数据）"""
    return {
        "layers": METHODOLOGY_LAYERS,
        "origins": {
            "note": "思想来源为卢麒元公开讲座思想提炼 + 马克思主义政治经济学公有领域理论；所有表达均为项目原创，不含第三方原文段落。",
            "source_registry": "docs/strategy_origins.md",
        },
        "method_version": "RIA-TV++-distilled-v1",
    }


@router.get("/strategies")
async def strategies(stage: str = Query("", description="按周期阶段筛选")):
    """策略库 — 按资本周期阶段分类"""
    if stage:
        return {"strategies": [s for s in STRATEGIES if s["stage"] == stage]}
    return {"strategies": STRATEGIES}


@router.get("/knowledge")
async def knowledge(category: str = Query("", description="按分类筛选")):
    """知识库文章"""
    if category:
        return {"articles": [a for a in KNOWLEDGE_ARTICLES if a["category"] == category]}
    return {
        "articles": KNOWLEDGE_ARTICLES,
        "categories": KNOWLEDGE_CATEGORIES,
    }
