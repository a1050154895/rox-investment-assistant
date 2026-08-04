"""选股筛选 API。"""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.services.screener_engine import PRESETS, run_scan

router = APIRouter()


class ScanFilters(BaseModel):
    change_pct_min: Optional[float] = Field(None, description="涨跌幅下限(%)")
    change_pct_max: Optional[float] = Field(None, description="涨跌幅上限(%)")
    turnover_min: Optional[float] = Field(None, description="换手率下限(%)")
    turnover_max: Optional[float] = Field(None, description="换手率上限(%)")
    pe_min: Optional[float] = Field(None, description="市盈率下限")
    pe_max: Optional[float] = Field(None, description="市盈率上限")
    pb_min: Optional[float] = Field(None, description="市净率下限")
    pb_max: Optional[float] = Field(None, description="市净率上限")
    market_cap_min: Optional[float] = Field(None, description="总市值下限(亿元)")
    market_cap_max: Optional[float] = Field(None, description="总市值上限(亿元)")
    industry: Optional[str] = Field(None, description="行业关键词")


@router.get("/presets")
async def presets():
    """获取预设策略列表。"""
    return {"presets": PRESETS}


@router.post("/scan")
async def scan(
    filters: ScanFilters | None = None,
    preset: str | None = Query(None, description="预设策略ID"),
    sort_by: str = Query("market_cap", description="排序字段"),
    sort_desc: bool = Query(True, description="降序"),
    limit: int = Query(50, ge=1, le=200, description="最多返回数量"),
):
    """执行选股扫描。可组合预设策略 + 自定义条件。"""
    filter_dict = filters.model_dump(exclude_none=True) if filters else None
    return await run_scan(
        filters=filter_dict,
        preset_id=preset,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
    )
