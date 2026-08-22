"""ETF 价格跟踪误差代理测试。"""
from app.services.fund_data import compute_tracking_proxy, TRACKING_INDEX


def _candles(closes, start_day=1):
    return [{"date": f"2026-01-{day:02d}", "close": close} for day, close in enumerate(closes, start_day)]


class TestTrackingProxy:
    def test_perfect_tracking_near_zero(self):
        closes = [100 * (1.01 ** i) for i in range(60)]
        etf = _candles(closes)
        index = _candles(closes)
        proxy = compute_tracking_proxy(etf, index)
        assert proxy is not None
        assert proxy["tracking_error_annualized_pct"] < 0.01
        assert proxy["correlation"] > 0.999
        assert proxy["sample_days"] == 59

    def test_noisy_tracking_larger_error(self):
        # ETF 收益在指数收益基础上叠加交替噪声 → 跟踪偏差波动大
        index_closes = [100 * (1.01 ** i) for i in range(60)]
        etf_closes = []
        price = 100.0
        for i in range(60):
            price *= 1.01 * (1.005 if i % 2 == 0 else 0.995)
            etf_closes.append(price)
        proxy = compute_tracking_proxy(_candles(etf_closes), _candles(index_closes))
        assert proxy["tracking_error_annualized_pct"] > 1
        assert 0 < proxy["correlation"] < 1

    def test_insufficient_samples_returns_none(self):
        proxy = compute_tracking_proxy(_candles([1, 2, 3]), _candles([1, 2, 3]))
        assert proxy is None

    def test_dates_aligned(self):
        # 指数缺某天时只按共同日期对齐
        etf = _candles([1 + i * 0.01 for i in range(30)])
        idx = _candles([2 + i * 0.02 for i in range(30)])[5:]
        proxy = compute_tracking_proxy(etf, idx)
        assert proxy is not None
        assert proxy["sample_days"] == 24

    def test_tracking_index_map_covers_supported_etfs(self):
        assert TRACKING_INDEX["510300"] == "000300"
        assert TRACKING_INDEX["159915"] == "399006"
        # 未映射的 ETF 保持不可用，不猜指数
        assert "512480" not in TRACKING_INDEX

    def test_fund_coverage_contract(self, client):
        data = client.get("/api/funds/510300").json()
        entry = data["evidence_coverage"]["tracking_error"]
        assert entry["status"] in ("available", "snapshot", "unavailable")
        if entry["status"] == "snapshot":
            assert "价格口径" in entry["message"] or "跟踪误差代理" in entry["message"]
