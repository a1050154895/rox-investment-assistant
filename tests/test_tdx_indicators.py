"""通达信风格指标数值测试（移植自 ROX3.0，重写为纯列表实现）。"""
from app.services.tdx_indicators import (
    barslast, count, filter_, peak_positions,
    pivots_summary, trough_positions, zig,
)


class TestBarsLastCountFilter:
    def test_barslast_basic(self):
        assert barslast([True, False, False, True, False]) == [0, 1, 2, 0, 1]

    def test_barslast_never_true_counts_from_start(self):
        assert barslast([False, False, False]) == [0, 1, 2]

    def test_count_window(self):
        assert count([True, True, True, False, False], 3) == [1, 2, 3, 2, 1]

    def test_filter_holds_signal(self):
        assert filter_([True, False, False, False], 2) == [True, True, False, False]
        assert filter_([False, True, False, False], 3) == [False, True, True, True]


class TestZigPivots:
    # 一个 V 型：100 → 120（+20%）→ 90（-25%）→ 110（+22%）
    CLOSES = [100, 105, 112, 120, 114, 105, 96, 90, 96, 103, 110]
    DATES = [f"2026-01-{i+1:02d}" for i in range(len(CLOSES))]

    def test_pivots_detected_at_8pct(self):
        peaks = peak_positions(self.CLOSES, 8)
        troughs = trough_positions(self.CLOSES, 8)
        assert 3 in peaks          # 120 峰
        assert 7 in troughs        # 90 谷
        assert self.CLOSES[3] == 120 and self.CLOSES[7] == 90

    def test_no_pivots_below_threshold(self):
        flat = [100, 101, 100.5, 101, 100.8]
        assert peak_positions(flat, 8) == []
        assert trough_positions(flat, 8) == []

    def test_zig_interpolates_between_pivots(self):
        line = zig(self.CLOSES, 8)
        assert line[3] == 120.0
        assert line[7] == 90.0
        # 3→7 之间线性插值
        assert line[5] == 120 + (90 - 120) * (5 - 3) / (7 - 3)

    def test_summary_carries_future_function_note(self):
        summary = pivots_summary(self.CLOSES, self.DATES, 8)
        assert "未来函数" in summary["note"]
        assert summary["pivot_count"] >= 2
        types = {p["type"] for p in summary["pivots"]}
        assert types == {"peak", "trough"}
        assert all(p["date"] for p in summary["pivots"])

    def test_last_pivot_is_provisional(self):
        # 末端新高尚未回撤确认时，最后极值被标记为临时峰（可被未来数据修正）
        rising = [100, 105, 112, 120, 125, 130]
        peaks = peak_positions(rising, 8)
        assert peaks == [len(rising) - 1]  # 无回撤 → 唯一峰是末端临时点
        troughs = trough_positions(rising, 8)
        assert 0 in troughs  # 起点被确认为初始谷
