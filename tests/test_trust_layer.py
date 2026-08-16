import asyncio
import unittest

from app.services.analysis_engine import build_analysis, calculate_indicators
from app.services.market_data import get_fund_flow, get_kline, get_stock_quote, normalize_stock_code


class TrustLayerTests(unittest.TestCase):
    def test_stock_code_normalization(self):
        self.assertEqual(normalize_stock_code("sh600519"), "600519")
        self.assertEqual(normalize_stock_code("600519.SH"), "600519")

    def test_analysis_is_deterministic(self):
        quote = {"price": 100, "pe": 20, "pb": 4}
        flow = {"main_inflow": 2.5}
        self.assertEqual(build_analysis(quote, flow), build_analysis(quote, flow))

    def test_indicators_refuse_short_series(self):
        result = calculate_indicators([{"close": 10}] * 10)
        self.assertEqual(result["data_status"], "unavailable")
        self.assertIsNone(result["rsi"])

    def test_unknown_stock_does_not_fabricate_data(self):
        quote = asyncio.run(get_stock_quote("999999"))
        flow = asyncio.run(get_fund_flow("999999"))
        kline = asyncio.run(get_kline("999999"))
        self.assertEqual(quote["data_status"], "unavailable")
        self.assertEqual(flow["data_status"], "unavailable")
        self.assertEqual(kline["data_status"], "unavailable")
        self.assertEqual(kline["candles"], [])
        self.assertIsNone(flow["main_inflow"])

    def test_market_indices_carry_freshness(self):
        from app.services.market_data import get_market_indices
        indices = asyncio.run(get_market_indices())
        self.assertTrue(indices)
        for idx in indices:
            self.assertIn("data_source", idx)
            self.assertIn("as_of", idx)
            self.assertIn("stale", idx)

    def test_capital_cycle_classification(self):
        from app.services.review_engine import classify_capital_cycle
        self.assertEqual(classify_capital_cycle(70, 70, 5, 0, 5, 2, 1.0), "流转")
        self.assertEqual(classify_capital_cycle(30, 35, 0, 5, 1, 6, -1.0), "再生产")
        self.assertEqual(classify_capital_cycle(50, 60, 1, 2, 2, 4, 0.5), "分配")
        self.assertEqual(classify_capital_cycle(48, 55, 2, 0, 4, 1, 0.3), "集中")
        self.assertEqual(classify_capital_cycle(50, 50, 1, 1, 2, 2, 0.0), "积累")
        # 信用扩张但价值承压 → 集中（即使盘面中性）
        self.assertEqual(classify_capital_cycle(50, 50, 1, 1, 2, 2, 0.0, credit_score=70, value_score=40), "集中")
        # 信用收缩 + 价值承压 + 盘面弱 → 再生产
        self.assertEqual(classify_capital_cycle(40, 50, 0, 1, 1, 2, -0.5, credit_score=40, value_score=40), "再生产")

    def test_capital_cycle_stage_shape(self):
        from app.services.review_engine import get_capital_cycle_stage
        result = asyncio.run(get_capital_cycle_stage(force=True))
        self.assertIn("stages", result)
        self.assertIn("stage_name", result)
        self.assertIn("signals", result)
        self.assertIn(result["stage_name"], ("积累", "集中", "流转", "分配", "再生产", "未评估"))

    def test_analyze_contradictions(self):
        from app.services.contradiction_engine import analyze_contradictions
        result = analyze_contradictions(
            index_avg=1.0, up_ratio=30.0, inflow=4, outflow=1,
            credit_score=70.0, real_score=40.0,
        )
        self.assertEqual([c["name"] for c in result], ["量价矛盾", "资金矛盾", "结构矛盾", "预期矛盾"])
        for c in result:
            self.assertGreaterEqual(c["intensity"], 0)
            self.assertLessEqual(c["intensity"], 100)
            self.assertIn("desc", c)
            self.assertIn("evidence", c)
        expectation = [c for c in result if c["key"] == "expectation"][0]
        self.assertGreater(expectation["intensity"], 0)
        self.assertEqual(expectation["trend"], "信用强、实体弱")

    def test_get_contradictions_shape(self):
        from app.services.contradiction_engine import get_contradictions
        result = asyncio.run(get_contradictions(force=True))
        for rank in ("primary", "secondary", "tertiary"):
            self.assertIn(rank, result)
            self.assertIn("name", result[rank])
            self.assertIn("intensity", result[rank])
        self.assertEqual(len(result["all"]), 4)

    def test_news_dedup(self):
        from app.services.intelligence_data import _dedup_news
        items = [
            {"title": "央行降息", "id": 1},
            {"title": "央行降息", "id": 2},
            {"title": " 央行 降息 ", "id": 3},
            {"title": "PMI数据公布", "id": 4},
        ]
        self.assertEqual(len(_dedup_news(items)), 2)


if __name__ == "__main__":
    unittest.main()
