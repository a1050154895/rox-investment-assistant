"""v4.45.0 — 多周期 MACD 状态矩阵、知识库增强（PDF/内置指引/高亮）、研究卡新模板。"""
import pytest

from app.services import knowledge_playbooks
from app.services.knowledge_base import rebuild, search
from app.services.macd_matrix import aggregate_monthly_to_quarters, macd_matrix, macd_series
from app.services.research_templates import RESEARCH_TEMPLATES


# ---------- MACD 序列与状态 ----------

class TestMacdSeries:
    def test_rising_series_turns_golden(self):
        closes = [10 + i * 0.5 for i in range(60)]  # 单边上行
        series = macd_series(closes)
        assert series[-1]["dif"] is not None and series[-1]["dif"] > 0
        assert series[-1]["dif"] > series[-1]["dea"]  # 上行末段 DIF 在 DEA 上方

    def test_falling_series_turns_death(self):
        closes = [50 - i * 0.5 for i in range(60)]  # 单边下行
        series = macd_series(closes)
        assert series[-1]["dif"] < 0
        assert series[-1]["dif"] < series[-1]["dea"]

    def test_insufficient_sample_returns_none(self):
        series = macd_series([1.0] * 10)
        assert len(series) == 10 and all(s["dif"] is None for s in series)


class TestQuarterAggregation:
    def test_monthly_bars_merge_into_quarters(self):
        bars = []
        for y, m in [(2025, 1), (2025, 2), (2025, 3), (2025, 4)]:
            bars.append({"date": f"{y}-{m:02d}-28", "open": 10.0, "close": 11.0 + m,
                         "high": 12.0 + m, "low": 9.0, "volume": 100})
        quarters = aggregate_monthly_to_quarters(bars)
        assert len(quarters) == 2
        assert quarters[0]["date"] == "2025Q1"
        assert quarters[0]["open"] == 10.0 and quarters[0]["close"] == 14.0  # 收取最后一个月
        assert quarters[0]["volume"] == 300


class TestMacdMatrixEndpoint:
    @pytest.fixture
    def fake_kline(self, monkeypatch):
        async def _fake(code, period="day", limit=120, is_index=False):
            n = {"day": 120, "week": 160, "month": 140}.get(period, 60)
            base = {"day": 0.05, "week": 0.3, "month": 1.2}[period]
            out = []
            for i in range(n):
                if period == "month":  # 月份必须递增，季度聚合才成立
                    d = f"{2015 + i // 12}-{(i % 12) + 1:02d}-15"
                else:
                    d = f"2026-{(i % 12) + 1:02d}-15"
                out.append({"date": d, "open": 10.0, "close": 10 + i * base,
                            "high": 11 + i * base, "low": 9.0, "volume": 1000})
            return out
        monkeypatch.setattr("app.services.macd_matrix.fetch_kline", _fake)

    async def _fetch(self, client):
        return client.get("/api/stock/600519/macd-matrix").json()

    def test_matrix_periods_and_honest_yearly(self, client, fake_kline):
        resp = client.get("/api/stock/600519/macd-matrix")
        assert resp.status_code == 200
        data = resp.json()
        by_period = {p["period"]: p for p in data["periods"]}
        assert set(by_period) == {"yearly", "quarterly", "monthly", "weekly", "daily"}
        # 年线样本不足必须诚实 unavailable
        assert by_period["yearly"]["data_status"] == "unavailable"
        # 其余周期有足够样本，状态可计算
        for p in ("quarterly", "monthly", "weekly", "daily"):
            assert by_period[p]["data_status"] == "realtime"
            assert by_period[p]["state"] in ("golden", "death")
        assert data["note"] and "不构成买卖信号" in data["note"]

    def test_matrix_all_sources_fail_degrades(self, client, monkeypatch):
        async def _fail(code, period="day", limit=120, is_index=False):
            return []
        monkeypatch.setattr("app.services.macd_matrix.fetch_kline", _fail)
        resp = client.get("/api/stock/600519/macd-matrix")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_status"] == "unavailable"
        assert all(p["data_status"] == "unavailable" for p in data["periods"])


# ---------- 研究卡模板 ----------

class TestResearchTemplates:
    def test_new_templates_registered(self):
        assert "multi_tf_macd_check" in RESEARCH_TEMPLATES
        assert "worst_case_first" in RESEARCH_TEMPLATES
        # 既有模板未被破坏
        for key in ("serenity_chain", "discipline_guard", "capital_flow_discipline"):
            assert key in RESEARCH_TEMPLATES

    def test_templates_api_exposes_new_cards(self, client):
        data = client.get("/api/research/templates").json()
        titles = " ".join(t.get("name", "") for t in (data if isinstance(data, list) else data.get("templates", [])))
        assert "多周期趋势状态自查" in titles
        assert "最坏情况先行" in titles


# ---------- 知识库增强 ----------

class TestKnowledgeEnhancements:
    def test_playbooks_search_and_list(self):
        hits = knowledge_playbooks.search_playbooks("MACD 多周期")
        assert hits and hits[0]["id"] == "pb_multi_tf_trend"
        listed = knowledge_playbooks.list_playbooks()
        assert listed["count"] >= 8
        for pb in listed["playbooks"]:
            assert pb["source"]  # 每条指引必须标注来源

    def test_playbooks_api_requires_auth(self, client):
        assert client.get("/api/knowledge/playbooks").status_code == 401

    def test_search_merges_builtin_with_source_label(self, client, auth_headers, tmp_path):
        # 准备一份用户文档
        (tmp_path / "my_notes.md").write_text("MACD 金叉与死叉的使用心得，配合成交量确认。", encoding="utf-8")
        rebuild(str(tmp_path))
        try:
            data = client.get("/api/knowledge/search?q=MACD", headers=auth_headers).json()
            assert data["builtin"], "内置指引应出现在检索结果中"
            assert all(b["source"] for b in data["builtin"])
            # 用户文档命中且片段带 [[ ]] 高亮标记
            user = [r for r in data["results"] if r["filename"] == "my_notes.md"]
            assert user and "[[" in user[0]["snippets"][0]
        finally:
            rebuild()  # 恢复真实知识目录索引，避免污染其他测试

    def test_pdf_garbage_skipped_without_crash(self, tmp_path):
        (tmp_path / "broken.pdf").write_bytes(b"%PDF-1.4 garbage not a real pdf")
        result = rebuild(str(tmp_path))
        assert result["doc_count"] == 0  # 损坏 PDF 如实跳过，不抛错

    def test_pdf_support_flag_reported(self, client, auth_headers):
        data = client.get("/api/knowledge/status", headers=auth_headers).json()
        assert "pdf_support" in data and "playbooks" in data


# ---------- 知识库递归索引与截断（v4.46） ----------

class TestKnowledgeRecursiveAndCaps:
    def test_recursive_subdirectory_indexing(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "inner.md").write_text("递归索引测试关键词斑马线", encoding="utf-8")
        (tmp_path / "top.txt").write_text("顶层文件", encoding="utf-8")
        result = rebuild(str(tmp_path))
        try:
            names = [d["filename"] for d in result["files"]]
            assert "sub/inner.md" in names and "top.txt" in names
            hits = search("斑马线")
            assert any("sub/inner.md" == r["filename"] for r in hits["results"])
        finally:
            rebuild()

    def test_oversize_doc_truncated_honestly(self, tmp_path, monkeypatch):
        import app.services.knowledge_base as kb
        monkeypatch.setattr(kb, "MAX_DOC_CHARS", 500)
        (tmp_path / "long.md").write_text("字" * 2000, encoding="utf-8")
        result = rebuild(str(tmp_path))
        try:
            doc = next(d for d in result["files"] if d["filename"] == "long.md")
            assert doc["truncated"] is True and doc["chars"] == 500
        finally:
            rebuild()

    def test_new_playbooks_registered(self):
        listed = knowledge_playbooks.list_playbooks()
        ids = [pb["id"] for pb in listed["playbooks"]]
        assert "pb_lin_senchi_quality" in ids
        assert "pb_community_strategy_audit" in ids
        assert listed["count"] == 10
