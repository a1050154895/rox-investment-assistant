"""新浪K线降级源测试（离线，不发真实请求）。"""
import json

from app.services.sina_data import _parse_rows, _sina_symbol
from app.services.data_source_registry import health_report


class TestSinaSymbol:
    def test_prefix_mapping(self):
        assert _sina_symbol("600519") == "sh600519"
        assert _sina_symbol("000001") == "sz000001"
        assert _sina_symbol("300750") == "sz300750"
        assert _sina_symbol("510300") == "sh510300"
        assert _sina_symbol("sh600519") == "sh600519"
        assert _sina_symbol("600519.XSHG") == "sh600519"


class TestParseRows:
    def test_parse_kline_payload(self):
        payload = json.dumps([
            {"day": "2026-08-21 15:00:00", "open": "10.00", "close": "10.50", "high": "10.60", "low": "9.90", "volume": "12300"},
            {"day": "2026-08-22 15:00:00", "open": "10.50", "close": "10.40", "high": "10.70", "low": "10.30", "volume": "9800"},
        ])
        candles = _parse_rows(payload)
        assert len(candles) == 2
        assert candles[0] == {"date": "2026-08-21", "open": 10.0, "close": 10.5, "high": 10.6, "low": 9.9, "volume": 12300}

    def test_bad_rows_skipped(self):
        payload = json.dumps([
            {"day": "2026-08-21", "open": "bad", "close": "10.5", "high": "10.6", "low": "9.9", "volume": "1"},
        ])
        assert _parse_rows(payload) == []


class TestRegistryEntry:
    def test_sina_kline_registered_with_degrade(self):
        report = health_report()
        src = next(s for s in report["sources"] if s["id"] == "sina_kline")
        assert src["name"] == "新浪K线直连"
        assert src["degrade_to"] == "neodata_snapshot"
        assert "K线" in src["data_types"]
