"""统一数据状态契约与 DataSourceRegistry 测试。"""
from app.services.data_contract import ensure_contract, normalize_status, status_block
from app.services.data_source_registry import health_report, record, record_result


class TestDataContract:
    def test_normalize_legacy_statuses(self):
        assert normalize_status("available") == "snapshot"
        assert normalize_status("degraded") == "partial"
        assert normalize_status("calculated") == "snapshot"
        assert normalize_status("realtime") == "realtime"
        assert normalize_status("") == "unavailable"
        assert normalize_status("whatever") == "unavailable"

    def test_status_block_shape(self):
        block = status_block("realtime", source="测试", as_of="2026-08-22")
        assert block["data_status"] == "realtime"
        assert block["stale"] is False
        assert block["coverage"] == "full"
        block = status_block(None)
        assert block["data_status"] == "unavailable"
        assert block["stale"] is True

    def test_ensure_contract_fills_missing_fields(self):
        payload = {"price": 10, "data_source": "腾讯自选股公开接口"}
        ensure_contract(payload, status="realtime", as_of="2026-08-22 10:00")
        assert payload["data_status"] == "realtime"
        assert payload["status_label"] == "实时"
        assert payload["price"] == 10

    def test_ensure_contract_maps_legacy(self):
        payload = {"data_status": "degraded", "message": "部分指标缺失"}
        ensure_contract(payload)
        assert payload["data_status"] == "partial"
        assert payload["coverage"] == "partial"


class TestDataSourceRegistry:
    def test_record_and_health(self):
        record("tencent_quote", ok=True, latency_ms=120)
        report = health_report()
        tencent = next(s for s in report["sources"] if s["id"] == "tencent_quote")
        assert tencent["health"] == "healthy"
        assert tencent["last_latency_ms"] == 120

        for _ in range(3):
            record("tencent_quote", ok=False, error="超时")
        report = health_report()
        tencent = next(s for s in report["sources"] if s["id"] == "tencent_quote")
        assert tencent["health"] == "down"
        assert tencent["consecutive_failures"] == 3
        record("tencent_quote", ok=True)
        assert next(s for s in health_report()["sources"] if s["id"] == "tencent_quote")["health"] == "healthy"

    def test_record_result_maps_source_name(self):
        record_result({"data_source": "新浪财经公开接口", "data_status": "realtime"})
        report = health_report()
        sina = next(s for s in report["sources"] if s["id"] == "sina_quote")
        assert sina["health"] == "healthy"

        record_result({"data_source": "NeoData 历史快照", "data_status": "snapshot", "stale": True})
        report = health_report()
        snapshot = next(s for s in report["sources"] if s["id"] == "neodata_snapshot")
        # 快照兜底在 record_result 中不算该源失败：它按 snapshot 记成功
        assert snapshot["consecutive_failures"] == 0

    def test_unknown_source_ignored(self):
        record_result({"data_source": "未知来源", "data_status": "realtime"})
        assert health_report()["summary"]["unknown"] >= 1

    def test_sources_api_requires_auth(self, client):
        assert client.get("/api/data/sources").status_code == 401

    def test_sources_api_returns_report(self, client, auth_headers):
        record("macro_official", ok=True)
        resp = client.get("/api/data/sources", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract"]["statuses"][0] == "realtime"
        assert any(s["id"] == "macro_official" for s in data["sources"])
