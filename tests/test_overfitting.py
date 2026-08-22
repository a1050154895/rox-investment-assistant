"""过拟合检查器测试。"""
from app.services.overfitting import _param_variants, oos_check, sensitivity_check

RUN_KW = {"commission_rate": 0, "slippage_rate": 0, "stamp_duty_rate": 0, "min_commission": 0}


def _candles(closes):
    return [{"date": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "open": c, "high": c * 1.01,
             "low": c * 0.99, "close": c, "volume": 1000} for i, c in enumerate(closes)]


class TestParamVariants:
    def test_variants_clamped_to_declared_range(self):
        variants = _param_variants("turtle_breakout", {"entry_period": 5, "exit_period": 40})
        values = {(k, v) for k, _, v in variants}
        # entry_period=5 下浮 4 会被钳回 min=5，只有上浮
        assert all(("entry_period", v) not in values or v >= 5 for _, _, v in [x for x in variants if x[0] == "entry_period"])
        assert all(v <= 40 for k, _, v in variants if k == "exit_period")

    def test_integer_params_stay_integer(self):
        for _, _, v in _param_variants("ma_cross", {"short_period": 5, "long_period": 20}):
            assert float(v).is_integer()


class TestSensitivity:
    def test_flat_market_base_nonpositive(self):
        candles = _candles([10] * 60)
        result = sensitivity_check(candles, "ma_cross", {"short_period": 5, "long_period": 20}, RUN_KW)
        assert result["cliff"] is False
        assert "基准收益非正" in result["verdict"]

    def test_rows_report_variant_returns(self):
        closes = [10 + (i % 10) * 0.2 + i * 0.05 for i in range(80)]
        result = sensitivity_check(_candles(closes), "ma_cross", {"short_period": 5, "long_period": 20}, RUN_KW)
        assert result["rows"]
        for row in result["rows"]:
            assert row["param"] and row["variant_return"] is not None


class TestOOS:
    def test_persistent_uptrend_is_robust(self):
        closes = [10 * (1.005 ** i) for i in range(120)]
        result = oos_check(_candles(closes), "ma_cross", {"short_period": 5, "long_period": 20}, RUN_KW)
        assert result["in_sample_return"] is not None
        assert "样本" in result["verdict"]

    def test_split_location_reported(self):
        closes = [10 + (i % 8) * 0.3 for i in range(100)]
        result = oos_check(_candles(closes), "ma_cross", {"short_period": 5, "long_period": 20}, RUN_KW)
        assert result["split_index"] == 70
        assert result["split_date"]
