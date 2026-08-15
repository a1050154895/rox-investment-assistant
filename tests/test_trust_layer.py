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

    def test_capital_cycle_stage_shape(self):
        from app.services.review_engine import get_capital_cycle_stage
        result = asyncio.run(get_capital_cycle_stage(force=True))
        self.assertIn("stages", result)
        self.assertIn("stage_name", result)
        self.assertIn("signals", result)
        self.assertIn(result["stage_name"], ("积累", "集中", "流转", "分配", "再生产", "未评估"))


if __name__ == "__main__":
    unittest.main()
