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


if __name__ == "__main__":
    unittest.main()
