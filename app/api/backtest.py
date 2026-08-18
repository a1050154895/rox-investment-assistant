"""回测引擎 API。"""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.core.capabilities import disabled_if
from app.services.backtest_engine import STRATEGIES, execute_backtest
from app.services.market_data import REAL_QUOTES

router = APIRouter()


class BacktestRequest(BaseModel):
    code: str = Field(..., description="6位A股代码")
    strategy: str = Field(..., description="策略ID")
    params: dict = Field(default_factory=dict, description="策略参数")
    period: str = Field("day", description="K线周期: day/week")
    kline_limit: int = Field(250, ge=60, le=500, description="K线根数")
    initial_capital: float = Field(100000, ge=10000, description="初始资金")
    commission_rate: float = Field(0.001, ge=0, le=0.01, description="手续费率")


@router.get("/strategies")
async def strategies():
    """获取可用策略列表。"""
    if (disabled := disabled_if("backtest")):
        return disabled
    return {"strategies": STRATEGIES}


@router.get("/stocks")
async def stock_list():
    """获取可选股票列表（内置池）。"""
    if (disabled := disabled_if("backtest")):
        return disabled
    stocks = [
        {"code": code, "name": info["name"], "industry": info.get("industry", "")}
        for code, info in REAL_QUOTES.items()
    ]
    return {"stocks": stocks}


@router.post("/run")
async def run(req: BacktestRequest):
    """执行回测。"""
    if (disabled := disabled_if("backtest")):
        return disabled
    name = REAL_QUOTES.get(req.code, {}).get("name", req.code)
    return await execute_backtest(
        code=req.code,
        name=name,
        strategy_id=req.strategy,
        params=req.params,
        period=req.period,
        kline_limit=req.kline_limit,
        initial_capital=req.initial_capital,
        commission_rate=req.commission_rate,
    )
