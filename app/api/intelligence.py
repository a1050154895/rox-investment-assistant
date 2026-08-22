"""宏观资讯与政策研判 API。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import ResearchCard, User, Watchlist as WatchlistItem
from app.services.data_contract import ensure_contract
from app.services.intel_themes import build_themes, mark_breaking, rank_for_user
from app.services.intelligence_data import get_intelligence_brief, get_stock_intelligence
from app.services.market_data import get_stock_quote

router = APIRouter()


@router.get("/brief")
async def intelligence_brief(refresh: bool = Query(False, description="是否刷新资讯缓存")):
    """公开资讯、政策、全球风险、行业资金流的一体化研判简报（含主题主线）。"""
    data = await get_intelligence_brief(force=refresh)
    news = mark_breaking(data.get("news", []))
    themes = build_themes(news, data.get("policy_tracker"))
    return ensure_contract(
        {
            **data,
            "news": news,
            "themes": themes,
        },
        status="realtime" if data.get("news") else "partial",
        data_source=data.get("source_status"),
    )


@router.get("/feed")
async def intelligence_feed(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """登录用户的情报流：按研究卡/自选关联度重排主题与资讯。

    排序依据可解释（研究关联度 → 突发 → 重要度），无情绪分、无涨跌预测。
    """
    brief = await get_intelligence_brief()
    cards = (
        db.query(ResearchCard)
        .filter(ResearchCard.user_id == user.id, ResearchCard.status != "archived")
        .order_by(ResearchCard.updated_at.desc())
        .limit(50)
        .all()
    )
    watchlist = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).limit(100).all()
    ranked = rank_for_user(
        build_themes(mark_breaking(brief.get("news", [])), brief.get("policy_tracker")),
        mark_breaking(brief.get("news", [])),
        cards=[card.to_dict() for card in cards],
        watchlist=[w.to_dict() for w in watchlist],
    )
    return ensure_contract(
        {**brief, **ranked},
        status="realtime" if brief.get("news") else "partial",
        data_source=brief.get("source_status"),
    )


@router.get("/concentration")
async def market_concentration(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """成交额集中度风险温度计（当日实时 + 自建历史快照）。"""
    from app.services.market_concentration import get_concentration
    return await get_concentration(db)


@router.get("/stock/{code}")
async def stock_intelligence(code: str):
    """个股所在行业与宏观资讯的传导路径。"""
    quote = await get_stock_quote(code)
    if "error" in quote:
        return quote
    return await get_stock_intelligence(code, quote.get("name", code), quote.get("industry", ""))
