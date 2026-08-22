"""回测引擎 v2：费用模型、止损止盈与绩效指标测试。"""
from app.services.backtest_engine import generate_signals, run_backtest


def _candle(date, close, high=None, low=None):
    return {"date": date, "open": close, "high": high or close, "low": low or close, "close": close, "volume": 1000}


def _flat_candles(closes):
    return [_candle(f"2026-01-{i+1:02d}", c) for i, c in enumerate(closes)]


class TestFeeModel:
    def test_zero_fees_pure_profit(self):
        # 10 元买 100 股，11 元卖，无费用 → 净利 100
        candles = _flat_candles([10, 11])
        result = run_backtest(candles, [1, -1], initial_capital=1500,
                              commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0)
        assert result["total_trades"] == 1
        assert result["final_equity"] == 1500 + 100
        assert abs(result["total_return"] - 6.67) < 0.01
        assert result["win_rate"] == 100.0

    def test_commission_and_stamp_duty_accounted(self):
        # 佣金 0.1% 双边 + 印花税 0.05% 卖出 + 最低佣金 5 元
        candles = _flat_candles([10, 11])
        result = run_backtest(candles, [1, -1], initial_capital=1500,
                              commission_rate=0.001, slippage_rate=0, stamp_duty_rate=0.0005, min_commission=5)
        buy_comm = max(100 * 10 * 0.001, 5)  # 5 元（触发最低佣金）
        sell_comm = max(100 * 11 * 0.001, 5)  # 5 元
        stamp = 100 * 11 * 0.0005  # 0.55 元
        expected_fees = buy_comm + sell_comm + stamp
        assert abs(result["total_fees"] - expected_fees) < 0.01
        expected_equity = 1500 - 100 * 10 - buy_comm + 100 * 11 - sell_comm - stamp
        assert abs(result["final_equity"] - expected_equity) < 0.01

    def test_slippage_worsens_both_sides(self):
        candles = _flat_candles([10, 11])
        result = run_backtest(candles, [1, -1], initial_capital=1500,
                              commission_rate=0, slippage_rate=0.01, stamp_duty_rate=0, min_commission=0)
        # 买入价 10.1，卖出价 10.89 → 仍盈利但少于无滑点
        assert result["final_equity"] == 1500 - 100 * 10.1 + 100 * 11 * 0.99
        assert result["final_equity"] < 1600


class TestStopLossTakeProfit:
    def test_stop_loss_triggers_at_stop_price(self):
        # 10 元买入，止损 8% → 触发价 9.2；当日最低 9.0 触发，按 9.2 成交
        candles = [
            _candle("2026-01-01", 10.0, high=10.2, low=9.9),
            _candle("2026-01-02", 9.3, high=9.5, low=9.0),
            _candle("2026-01-03", 9.4, high=9.6, low=9.2),
        ]
        result = run_backtest(candles, [1, 0, 0], initial_capital=10000,
                              commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0,
                              stop_loss_pct=0.08)
        sells = [t for t in result["trades"] if t["action"] == "止损卖出"]
        assert len(sells) == 1
        assert sells[0]["price"] == 9.2
        assert result["total_trades"] == 1

    def test_take_profit_triggers(self):
        candles = [
            _candle("2026-01-01", 10.0, high=10.1, low=9.9),
            _candle("2026-01-02", 11.5, high=11.8, low=11.0),
        ]
        result = run_backtest(candles, [1, 0], initial_capital=10000,
                              commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0,
                              take_profit_pct=0.1)
        sells = [t for t in result["trades"] if t["action"] == "止盈卖出"]
        assert len(sells) == 1
        assert sells[0]["price"] == 11.0  # 10 * 1.1

    def test_no_stop_no_trigger(self):
        candles = [_candle("2026-01-01", 10.0), _candle("2026-01-02", 10.5)]
        result = run_backtest(candles, [1, 0], initial_capital=10000,
                              commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0,
                              stop_loss_pct=0.5)
        assert result["total_trades"] == 1
        assert result["trades"][-1]["action"] == "期末平仓"


class TestMetrics:
    def test_position_pct_halves_exposure(self):
        candles = _flat_candles([10, 12])
        full = run_backtest(candles, [1, -1], initial_capital=100000,
                            commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0)
        half = run_backtest(candles, [1, -1], initial_capital=100000,
                            commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0,
                            position_pct=0.5)
        assert full["total_return"] == 20.0
        assert abs(half["total_return"] - 10.0) < 0.1

    def test_profit_factor_and_avg(self):
        # 构造两笔盈利一笔亏损：10→12（+20%）、9→9.5（+5.5%）、10→9（-10%）
        candles = _flat_candles([10, 12, 9, 9.5, 10, 9, 8.9])
        signals = [1, -1, 1, -1, 1, -1, 0]
        result = run_backtest(candles, signals, initial_capital=100000,
                              commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0)
        assert result["total_trades"] == 3
        assert result["win_count"] == 2
        assert result["loss_count"] == 1
        assert result["profit_factor"] > 1
        assert result["avg_win"] > 0
        assert result["avg_loss"] < 0
        assert result["avg_holding_days"] == 1.0  # 每笔隔日

    def test_sharpe_none_when_flat_or_short(self):
        candles = _flat_candles([10, 10, 10])
        result = run_backtest(candles, [0, 0, 0], initial_capital=10000)
        assert result["sharpe_ratio"] is None

    def test_holding_days_counted(self):
        candles = [
            _candle("2026-01-01", 10.0), _candle("2026-01-05", 11.0),
        ]
        result = run_backtest(candles, [1, -1], initial_capital=10000,
                              commission_rate=0, slippage_rate=0, stamp_duty_rate=0, min_commission=0)
        assert result["avg_holding_days"] == 4.0


class TestAbsorbedStrategies:
    # 海龟突破：横盘后放量突破
    def _candles_from_closes(self, closes):
        return [{"date": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "open": c, "high": c * 1.01,
                 "low": c * 0.99, "close": c, "volume": 1000} for i, c in enumerate(closes)]

    def test_turtle_breakout_buys_on_channel_high(self):
        closes = [10] * 25 + [11.5]
        signals = generate_signals(
            "turtle_breakout", self._candles_from_closes(closes), {"entry_period": 20, "exit_period": 10})
        assert signals[25] == 1  # 突破前20日高点

    def test_turtle_exits_on_channel_low(self):
        closes = [10] * 25 + [11.5] + [11.0] * 5 + [9.0]
        signals = generate_signals(
            "turtle_breakout", self._candles_from_closes(closes), {"entry_period": 20, "exit_period": 5})
        assert 1 in signals
        assert signals[-1] == -1  # 跌破近5日低点

    def test_turtle_no_signal_in_flat_range(self):
        closes = [10] * 30
        signals = generate_signals(
            "turtle_breakout", self._candles_from_closes(closes), {"entry_period": 20, "exit_period": 10})
        assert signals == [0] * 30

    def test_momentum_enters_above_threshold(self):
        closes = [10] * 21 + [10.6]  # 20日动量 6% > 5%
        signals = generate_signals("momentum", self._candles_from_closes(closes), {"lookback": 20, "threshold_pct": 5})
        assert signals[-1] == 1

    def test_momentum_exits_when_negative(self):
        closes = [11] * 21 + [10.5]  # 20日动量 (10.5/11-1) = -4.5% 转负
        signals = generate_signals("momentum", self._candles_from_closes(closes), {"lookback": 20, "threshold_pct": 5})
        assert signals[-1] == -1

    def test_momentum_flat_no_signal(self):
        closes = [10] * 25
        signals = generate_signals("momentum", self._candles_from_closes(closes), {"lookback": 20, "threshold_pct": 5})
        assert not any(signals)
