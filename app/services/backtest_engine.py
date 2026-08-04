"""ROX 回测引擎 — 基于历史 K 线的策略验证框架。

定位：框架验证 / 经验沉淀工具，不输出买卖信号。
用户选择策略 + 股票 + 参数 → 引擎用历史 K 线模拟 → 输出收益率/回撤/胜率/交易记录。
结果仅用于校准认知框架，不代表未来收益。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.services.tencent_data import fetch_kline

logger = logging.getLogger(__name__)

# ============ 策略定义 ============

STRATEGIES: list[dict[str, Any]] = [
    {
        "id": "ma_cross",
        "name": "均线交叉",
        "description": "短期均线上穿长期均线买入，下穿卖出。经典趋势跟踪策略。",
        "params": [
            {"key": "short_period", "label": "短期均线天数", "default": 5, "min": 2, "max": 30},
            {"key": "long_period", "label": "长期均线天数", "default": 20, "min": 5, "max": 120},
        ],
    },
    {
        "id": "rsi_oversold",
        "name": "RSI 超卖反弹",
        "description": "RSI 低于超卖线时买入，高于超买线时卖出。逆势策略。",
        "params": [
            {"key": "rsi_period", "label": "RSI 计算周期", "default": 14, "min": 5, "max": 30},
            {"key": "oversold", "label": "超卖线", "default": 30, "min": 10, "max": 40},
            {"key": "overbought", "label": "超买线", "default": 70, "min": 60, "max": 90},
        ],
    },
    {
        "id": "bbands_squeeze",
        "name": "布林带收窄突破",
        "description": "布林带收窄后价格突破上轨买入，跌破中轨卖出。波动率突破策略。",
        "params": [
            {"key": "bb_period", "label": "布林带周期", "default": 20, "min": 5, "max": 60},
            {"key": "bb_std", "label": "标准差倍数", "default": 2.0, "min": 1.0, "max": 3.0},
        ],
    },
    {
        "id": "macd_cross",
        "name": "MACD 金叉死叉",
        "description": "MACD 金叉（DIF上穿DEA）买入，死叉卖出。动量策略。",
        "params": [
            {"key": "fast", "label": "快线周期", "default": 12, "min": 5, "max": 30},
            {"key": "slow", "label": "慢线周期", "default": 26, "min": 10, "max": 60},
            {"key": "signal", "label": "信号线周期", "default": 9, "min": 3, "max": 20},
        ],
    },
]


def _sma(closes: list[float], period: int) -> list[float | None]:
    """简单移动平均。"""
    result: list[float | None] = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            window = closes[i - period + 1: i + 1]
            result.append(sum(window) / period)
    return result


def _ema(closes: list[float], period: int) -> list[float]:
    """指数移动平均。"""
    if not closes:
        return []
    k = 2 / (period + 1)
    result = [closes[0]]
    for i in range(1, len(closes)):
        result.append(closes[i] * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int) -> list[float | None]:
    """相对强弱指标。"""
    result: list[float | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return result
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period, len(closes)):
        if i > period:
            diff = closes[i] - closes[i - 1]
            gain = max(diff, 0)
            loss = max(-diff, 0)
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - 100 / (1 + rs)
    return result


def _bollinger(closes: list[float], period: int, std_mult: float) -> list[dict]:
    """布林带（上轨、中轨、下轨）。"""
    result: list[dict] = [{}] * len(closes)
    sma = _sma(closes, period)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1: i + 1]
        mid = sma[i]
        variance = sum((x - mid) ** 2 for x in window) / period
        std = variance ** 0.5
        result[i] = {
            "mid": mid,
            "upper": mid + std_mult * std,
            "lower": mid - std_mult * std,
            "width": std_mult * std * 2,
        }
    return result


def _macd(closes: list[float], fast: int, slow: int, signal: int) -> list[dict]:
    """MACD 指标。"""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea = _ema(dif, signal)
    return [{"dif": d, "dea": e, "hist": d - e} for d, e in zip(dif, dea)]


# ============ 信号生成 ============

def generate_signals(strategy_id: str, candles: list[dict], params: dict) -> list[int]:
    """生成交易信号：1=买入, -1=卖出, 0=持有/无信号。"""
    n = len(candles)
    closes = [c["close"] for c in candles]
    signals = [0] * n

    if strategy_id == "ma_cross":
        sp = int(params.get("short_period", 5))
        lp = int(params.get("long_period", 20))
        short_ma = _sma(closes, sp)
        long_ma = _sma(closes, lp)
        for i in range(lp + 1, n):
            if short_ma[i] is None or long_ma[i] is None or short_ma[i - 1] is None or long_ma[i - 1] is None:
                continue
            # 金叉
            if short_ma[i - 1] <= long_ma[i - 1] and short_ma[i] > long_ma[i]:
                signals[i] = 1
            # 死叉
            elif short_ma[i - 1] >= long_ma[i - 1] and short_ma[i] < long_ma[i]:
                signals[i] = -1

    elif strategy_id == "rsi_oversold":
        rp = int(params.get("rsi_period", 14))
        oversold = float(params.get("oversold", 30))
        overbought = float(params.get("overbought", 70))
        rsi = _rsi(closes, rp)
        for i in range(rp + 1, n):
            if rsi[i] is None or rsi[i - 1] is None:
                continue
            if rsi[i - 1] < oversold and rsi[i] >= oversold:
                signals[i] = 1
            elif rsi[i - 1] < overbought and rsi[i] >= overbought:
                signals[i] = -1

    elif strategy_id == "bbands_squeeze":
        bp = int(params.get("bb_period", 20))
        bs = float(params.get("bb_std", 2.0))
        bb = _bollinger(closes, bp, bs)
        for i in range(bp + 1, n):
            if not bb[i] or not bb[i - 1]:
                continue
            # 收窄判断：前一根 width 低于近 20 根最小值
            if i >= bp + 20:
                widths = [bb[j].get("width", 0) for j in range(i - 20, i) if bb[j]]
                if widths and bb[i]["width"] > max(widths) * 1.5:
                    if closes[i] > bb[i]["upper"]:
                        signals[i] = 1
            if closes[i] < bb[i].get("mid", 0) and closes[i - 1] >= bb[i - 1].get("mid", 0):
                signals[i] = -1

    elif strategy_id == "macd_cross":
        f = int(params.get("fast", 12))
        s = int(params.get("slow", 26))
        sig = int(params.get("signal", 9))
        macd = _macd(closes, f, s, sig)
        for i in range(s + sig, n):
            if macd[i]["dif"] is None or macd[i - 1]["dif"] is None:
                continue
            # 金叉
            if macd[i - 1]["dif"] <= macd[i - 1]["dea"] and macd[i]["dif"] > macd[i]["dea"]:
                signals[i] = 1
            # 死叉
            elif macd[i - 1]["dif"] >= macd[i - 1]["dea"] and macd[i]["dif"] < macd[i]["dea"]:
                signals[i] = -1

    return signals


# ============ 回测执行 ============

def run_backtest(
    candles: list[dict],
    signals: list[int],
    initial_capital: float = 100000.0,
    commission_rate: float = 0.001,
) -> dict[str, Any]:
    """执行回测，返回收益统计与交易记录。"""
    n = len(candles)
    if n < 2:
        return {"error": "K线数据不足"}

    capital = initial_capital
    position = 0  # 持有股数
    entry_price = 0.0
    trades: list[dict] = []
    equity_curve: list[dict] = []
    max_equity = initial_capital
    max_drawdown = 0.0
    win_count = 0
    loss_count = 0

    for i in range(n):
        date = candles[i]["date"]
        close = candles[i]["close"]
        signal = signals[i]

        # 执行信号
        if signal == 1 and position == 0:
            # 买入（全仓）
            shares = int(capital / (close * (1 + commission_rate)) / 100) * 100
            if shares > 0:
                cost = shares * close * (1 + commission_rate)
                capital -= cost
                position = shares
                entry_price = close
                trades.append({
                    "date": date, "action": "买入", "price": round(close, 2),
                    "shares": shares, "cost": round(cost, 2), "capital": round(capital, 2),
                })

        elif signal == -1 and position > 0:
            # 卖出
            revenue = position * close * (1 - commission_rate)
            capital += revenue
            pnl = (close - entry_price) * position - position * close * commission_rate * 2
            if pnl > 0:
                win_count += 1
            else:
                loss_count += 1
            trades.append({
                "date": date, "action": "卖出", "price": round(close, 2),
                "shares": position, "revenue": round(revenue, 2),
                "capital": round(capital, 2), "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / (entry_price * position) * 100, 2) if entry_price > 0 else 0,
            })
            position = 0
            entry_price = 0.0

        # 记录每日权益
        equity = capital + position * close
        equity_curve.append({"date": date, "equity": round(equity, 2)})
        if equity > max_equity:
            max_equity = equity
        dd = (max_equity - equity) / max_equity * 100 if max_equity > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # 末尾平仓
    if position > 0:
        close = candles[-1]["close"]
        revenue = position * close * (1 - commission_rate)
        capital += revenue
        pnl = (close - entry_price) * position - position * close * commission_rate * 2
        if pnl > 0:
            win_count += 1
        else:
            loss_count += 1
        trades.append({
            "date": candles[-1]["date"], "action": "期末平仓", "price": round(close, 2),
            "shares": position, "revenue": round(revenue, 2),
            "capital": round(capital, 2), "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / (entry_price * position) * 100, 2) if entry_price > 0 else 0,
        })

    final_equity = capital
    total_return = (final_equity - initial_capital) / initial_capital * 100
    total_trades = win_count + loss_count
    win_rate = win_count / total_trades * 100 if total_trades > 0 else 0
    buy_hold_return = (candles[-1]["close"] - candles[0]["close"]) / candles[0]["close"] * 100

    return {
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return": round(total_return, 2),
        "buy_hold_return": round(buy_hold_return, 2),
        "excess_return": round(total_return - buy_hold_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 1),
        "trades": trades,
        "equity_curve": equity_curve,
        "candle_count": n,
        "start_date": candles[0]["date"],
        "end_date": candles[-1]["date"],
    }


async def execute_backtest(
    code: str,
    name: str,
    strategy_id: str,
    params: dict,
    period: str = "day",
    kline_limit: int = 250,
    initial_capital: float = 100000.0,
    commission_rate: float = 0.001,
) -> dict[str, Any]:
    """完整回测流程：获取K线 → 生成信号 → 执行回测。"""
    candles = await fetch_kline(code, period=period, limit=kline_limit)
    if not candles or len(candles) < 30:
        return {
            "error": "K线数据不足，至少需要 30 根K线",
            "code": code, "name": name,
        }

    signals = generate_signals(strategy_id, candles, params)
    result = run_backtest(candles, signals, initial_capital, commission_rate)
    if "error" in result:
        return {**result, "code": code, "name": name}

    return {
        "code": code,
        "name": name,
        "strategy_id": strategy_id,
        "strategy_name": next((s["name"] for s in STRATEGIES if s["id"] == strategy_id), strategy_id),
        "params": params,
        "period": period,
        **result,
        "disclaimer": "回测结果仅用于框架验证和经验沉淀，不代表未来收益。历史表现不构成投资建议。",
        "run_at": datetime.now().isoformat(),
    }
