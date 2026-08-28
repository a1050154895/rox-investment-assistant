"""场内基金搜索与通用详情的离线契约测试。"""
import asyncio

from app.services import fund_data
from app.services import tencent_data

# conftest 的 autouse 夹具会把 smartbox 换成空实现；解析测试保留原始函数。
_original_smartbox = tencent_data.smartbox_search


def test_search_funds_falls_through_to_marketwide_fund_search(monkeypatch):
    async def _smartbox(query, limit=10):
        assert query == "易方达"
        return [
            {"code": "161005", "name": "易方达精选LOF", "symbol": "sz161005"},
            {"code": "510300", "name": "沪深300ETF", "symbol": "sh510300"},
        ]

    monkeypatch.setattr(fund_data, "smartbox_search", _smartbox)
    results = asyncio.run(fund_data.search_funds("易方达"))
    assert results[0]["code"] == "161005"
    assert results[0]["fund_type"] == "场内基金"


def test_generic_fund_detail_keeps_unknown_fields_honest(monkeypatch):
    quote = {
        "code": "161005", "name": "易方达精选LOF", "price": 1.23,
        "change_pct": 0.1, "data_status": "realtime", "data_source": "测试行情",
        "as_of": "2026-08-28", "stale": False,
    }

    async def _quote(code):
        return quote

    async def _tracking(code):
        return {"status": "unavailable", "message": "跟踪标的待核验"}

    monkeypatch.setattr(fund_data, "get_stock_quote", _quote)
    monkeypatch.setattr(fund_data, "_tracking_error_entry", _tracking)
    fund = asyncio.run(fund_data.get_fund("161005"))
    assert fund["name"] == "易方达精选LOF"
    assert fund["fund_type"] == "场内基金"
    assert fund["tracking"] == "待核验"
    assert fund["evidence_coverage"]["nav"]["status"] == "unavailable"


def test_smartbox_search_accepts_etf_and_lof_types(monkeypatch):
    class _Response:
        content = (
            'v_hint="sh~518880~黄金ETF~hjetf~ETF^'
            'sz~161131~易方达科润LOF~yfdklof~LOF^'
            'sh~600519~贵州茅台~gzmt~GP-A"'
        ).encode("gbk")

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return _Response()

    class _HTTPX:
        AsyncClient = _Client

    monkeypatch.setattr(tencent_data, "httpx", _HTTPX)
    monkeypatch.setattr(tencent_data, "smartbox_search", _original_smartbox)
    results = asyncio.run(tencent_data.smartbox_search("易方达"))
    assert [(item["code"], item["symbol"]) for item in results] == [
        ("518880", "sh518880"),
        ("161131", "sz161131"),
        ("600519", "sh600519"),
    ]
