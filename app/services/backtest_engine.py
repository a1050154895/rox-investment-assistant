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
    {
        "id": "turtle_breakout",
        "name": "海龟突破（Donchian 通道）",
        "description": "收盘价突破前 N 日最高价买入，跌破前 M 日最低价卖出。趋势跟踪经典（策略知识重写自 ROX3 书籍策略库）。",
        "params": [
            {"key": "entry_period", "label": "入场通道天数", "default": 20, "min": 5, "max": 60},
            {"key": "exit_period", "label": "出场通道天数", "default": 10, "min": 3, "max": 40},
        ],
    },
    {
        "id": "momentum",
        "name": "动量策略",
        "description": "N 日收益率动量超过阈值买入，动量转负卖出。ETF 轮动的单标的动量内核（重写自 ROX3 轮动策略思想）。",
        "params": [
            {"key": "lookback", "label": "动量回看天数", "default": 20, "min": 5, "max": 120},
            {"key": "threshold_pct", "label": "入场动量阈值%", "default": 5, "min": 0, "max": 30},
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

    elif strategy_id == "turtle_breakout":
        entry_p = int(params.get("entry_period", 20))
        exit_p = int(params.get("exit_period", 10))
        highs = [c["high"] if c.get("high") is not None else c["close"] for c in candles]
        lows = [c["low"] if c.get("low") is not None else c["close"] for c in candles]
        for i in range(entry_p, n):
            channel_high = max(highs[i - entry_p:i])
            channel_low = min(lows[i - exit_p:i]) if i >= exit_p else None
            # 突破前 N 日最高价（不含当日）入场
            if closes[i] > channel_high and closes[i - 1] <= max(highs[i - 1 - entry_p:i - 1]):
                signals[i] = 1
            # 跌破前 M 日最低价离场
            elif channel_low is not None and closes[i] < channel_low:
                signals[i] = -1

    elif strategy_id == "momentum":
        lookback = int(params.get("lookback", 20))
        threshold = float(params.get("threshold_pct", 5))
        for i in range(lookback, n):
            if closes[i - lookback] <= 0:
                continue
            momentum = (closes[i] / closes[i - lookback] - 1) * 100
            prev_ref = closes[i - 1 - lookback] if i - 1 - lookback >= 0 else None
            prev_momentum = (closes[i - 1] / prev_ref - 1) * 100 if prev_ref else None
            # 动量上穿阈值入场；动量转负离场
            if prev_momentum is not None and prev_momentum <= threshold < momentum:
                signals[i] = 1
            elif momentum < 0:
                signals[i] = -1

    return signals


# ============ 回测执行 ============

def _parse_date(text: str) -> datetime | None:
    try:
        return datetime.strptime(str(text)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def run_backtest(
    candles: list[dict],
    signals: list[int],
    initial_capital: float = 100000.0,
    commission_rate: float = 0.001,
    slippage_rate: float = 0.0001,
    stamp_duty_rate: float = 0.0005,
    min_commission: float = 5.0,
    position_pct: float = 1.0,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    risk_free_rate: float = 0.02,
) -> dict[str, Any]:
    """执行回测，返回收益统计与交易记录。

    费用模型（吸收自 ROX3.0 回测引擎）：佣金双边、卖出印花税、
    滑点按不利方向计入成交价、最低佣金；支持盘中止损/止盈（触发价成交）。
    """
    n = len(candles)
    if n < 2:
        return {"error": "K线数据不足"}

    capital = initial_capital
    position = 0  # 持有股数
    entry_price = 0.0  # 含滑点的买入成交价
    entry_commission = 0.0
    entry_date = None
    trades: list[dict] = []
    equity_curve: list[dict] = []
    max_equity = initial_capital
    max_drawdown = 0.0
    closed: list[dict] = []  # 已配对交易（含净盈亏）
    total_fees = 0.0

    def _sell(i: int, raw_price: float, reason: str) -> None:
        """按成交价平仓：滑点、佣金、印花税一次算清。"""
        nonlocal capital, position, entry_price, entry_commission, entry_date, total_fees
        fill = raw_price * (1 - slippage_rate)
        commission = max(position * raw_price * commission_rate, min_commission)
        stamp = position * raw_price * stamp_duty_rate
        revenue = position * fill - commission - stamp
        capital += revenue
        fees = entry_commission + commission + stamp
        total_fees += commission + stamp  # 买入佣金在开仓时已计入
        pnl = (fill - entry_price) * position - fees
        entry_cost = entry_price * position + entry_commission
        start = _parse_date(entry_date) if entry_date else None
        end = _parse_date(candles[i]["date"])
        holding_days = (end - start).days if start and end else None
        trades.append({
            "date": candles[i]["date"], "action": reason, "price": round(raw_price, 2),
            "shares": position, "revenue": round(revenue, 2),
            "capital": round(capital, 2), "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / entry_cost * 100, 2) if entry_cost > 0 else 0,
            "fees": round(fees, 2), "holding_days": holding_days,
        })
        closed.append(trades[-1])
        position = 0
        entry_price = 0.0
        entry_commission = 0.0
        entry_date = None

    for i in range(n):
        close = candles[i]["close"]
        high = candles[i].get("high", close)
        low = candles[i].get("low", close)

        # 盘中风控优先于信号：先止损（保守），再止盈
        if position > 0 and stop_loss_pct:
            stop_price = entry_price * (1 - stop_loss_pct)
            if low <= stop_price:
                _sell(i, stop_price, "止损卖出")
        if position > 0 and take_profit_pct:
            tp_price = entry_price * (1 + take_profit_pct)
            if high >= tp_price:
                _sell(i, tp_price, "止盈卖出")

        signal = signals[i]
        if signal == 1 and position == 0:
            fill = close * (1 + slippage_rate)
            budget = capital * min(max(position_pct, 0.01), 1.0)
            shares = int(budget / (fill * (1 + commission_rate)) / 100) * 100
            if shares >= 100:
                commission = max(shares * close * commission_rate, min_commission)
                cost = shares * fill + commission
                if cost <= capital:
                    capital -= cost
                    total_fees += commission
                    position = shares
                    entry_price = fill
                    entry_commission = commission
                    entry_date = candles[i]["date"]
                    trades.append({
                        "date": candles[i]["date"], "action": "买入", "price": round(fill, 2),
                        "shares": shares, "cost": round(cost, 2), "capital": round(capital, 2),
                        "fees": round(commission, 2),
                    })
        elif signal == -1 and position > 0:
            _sell(i, close, "卖出")

        # 记录每日权益
        equity = capital + position * close
        equity_curve.append({"date": candles[i]["date"], "equity": round(equity, 2)})
        if equity > max_equity:
            max_equity = equity
        dd = (max_equity - equity) / max_equity * 100 if max_equity > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # 末尾平仓
    if position > 0:
        _sell(n - 1, candles[-1]["close"], "期末平仓")

    final_equity = capital
    total_return = (final_equity - initial_capital) / initial_capital * 100
    win_trades = [t for t in closed if t["pnl"] > 0]
    loss_trades = [t for t in closed if t["pnl"] <= 0]
    total_trades = len(closed)
    win_rate = len(win_trades) / total_trades * 100 if total_trades > 0 else 0
    gross_win = sum(t["pnl"] for t in win_trades)
    gross_loss = sum(abs(t["pnl"]) for t in loss_trades)
    profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else None
    holding_days_list = [t["holding_days"] for t in closed if t["holding_days"] is not None]
    avg_holding = round(sum(holding_days_list) / len(holding_days_list), 1) if holding_days_list else None

    # 夏普比率：日收益年化（净值序列），减无风险日利率
    sharpe = None
    if len(equity_curve) > 20:
        values = [e["equity"] for e in equity_curve]
        rets = [(values[i] / values[i - 1] - 1) for i in range(1, len(values)) if values[i - 1] > 0]
        if len(rets) > 20:
            mean_ret = sum(rets) / len(rets)
            variance = sum((r - mean_ret) ** 2 for r in rets) / len(rets)
            std = variance ** 0.5
            if std > 0:
                sharpe = round((mean_ret - risk_free_rate / 252) / std * (252 ** 0.5), 2)

    buy_hold_return = (candles[-1]["close"] - candles[0]["close"]) / candles[0]["close"] * 100

    return {
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return": round(total_return, 2),
        "buy_hold_return": round(buy_hold_return, 2),
        "excess_return": round(total_return - buy_hold_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": sharpe,
        "profit_factor": profit_factor,
        "avg_win": round(gross_win / len(win_trades), 2) if win_trades else None,
        "avg_loss": round(-gross_loss / len(loss_trades), 2) if loss_trades else None,
        "avg_holding_days": avg_holding,
        "total_fees": round(total_fees, 2),
        "total_trades": total_trades,
        "win_count": len(win_trades),
        "loss_count": len(loss_trades),
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
    slippage_rate: float = 0.0001,
    stamp_duty_rate: float = 0.0005,
    min_commission: float = 5.0,
    position_pct: float = 1.0,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
) -> dict[str, Any]:
    """完整回测流程：获取K线 → 生成信号 → 执行回测。"""
    candles = await fetch_kline(code, period=period, limit=kline_limit)
    if not candles or len(candles) < 30:
        return {
            "error": "K线数据不足，至少需要 30 根K线",
            "code": code, "name": name,
        }

    signals = generate_signals(strategy_id, candles, params)
    run_kwargs = {
        "initial_capital": initial_capital,
        "commission_rate": commission_rate,
        "slippage_rate": slippage_rate,
        "stamp_duty_rate": stamp_duty_rate,
        "min_commission": min_commission,
        "position_pct": position_pct,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
    }
    result = run_backtest(candles, signals, **run_kwargs)
    if "error" in result:
        return {**result, "code": code, "name": name}

    # 过拟合检查：参数敏感性 + 样本内外对比（默认开启，纯计算无额外请求）
    overfit = None
    if len(candles) >= 80:
        try:
            from app.services.overfitting import full_check
            overfit = full_check(candles, strategy_id, params, run_kwargs)
        except Exception as exc:  # noqa: BLE001 — 检查失败不影响回测结果
            logger.warning("过拟合检查失败: %s", exc)
            overfit = None

    return {
        "code": code,
        "name": name,
        "strategy_id": strategy_id,
        "strategy_name": next((s["name"] for s in STRATEGIES if s["id"] == strategy_id), strategy_id),
        "params": params,
        "period": period,
        "kline_source": "腾讯前复权日/周K线（公开接口）",
        "overfit": overfit,
        **result,
        "disclaimer": "回测基于公开前复权K线与费用模型（佣金/印花税/滑点），仅用于框架验证和经验沉淀，不代表未来收益。",
        "run_at": datetime.now().isoformat(),
    }
