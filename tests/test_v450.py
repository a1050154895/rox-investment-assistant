"""宏观行业漏斗测试：规则匹配确定性、行业排序、候选池排序与非建议声明。"""
import pandas as pd
import pytest

from app.services import macro_funnel
from app.services.macro_funnel import evaluate_rules, get_candidate_pool, rank_industries


def _matrix(fiscal=70.0, value=50.0, m2=None, pmi=None, real_rate=None, real_status=None):
    def _indicator(key, value, status="available"):
        return {"key": key, "value": value, "status": status}
    return {
        "sovereign_credit": {"score": fiscal, "indicators": [_indicator("m2_yoy", m2), _indicator("pmi", pmi)]},
        "value_realization": {"score": value, "indicators": []},
        "real_rate_proxy": {"value": real_rate, "status": real_status},
    }


class TestRuleMatching:
    def test_fiscal_expansion_matches_growth_rule(self):
        matched = evaluate_rules(_matrix(fiscal=70.0))
        assert any(r["id"] == "fiscal_expand" for r in matched)
        assert all(r["id"] != "fiscal_contract" for r in matched)

    def test_fiscal_contraction_matches_defensive_rule(self):
        matched = evaluate_rules(_matrix(fiscal=40.0))
        assert any(r["id"] == "fiscal_contract" for r in matched)

    def test_neutral_matrix_matches_nothing(self):
        assert evaluate_rules(_matrix(fiscal=52.0, value=52.0, m2=8.0, pmi=50.0)) == []

    def test_real_rate_rule_requires_calculated_status(self):
        # 快照/未计算状态下的实质利率不得触发规则
        matched = evaluate_rules(_matrix(fiscal=70.0, real_rate=-1.0, real_status="unavailable"))
        assert all(r["id"] != "real_rate_low" for r in matched)
        matched2 = evaluate_rules(_matrix(fiscal=70.0, real_rate=-1.0, real_status="calculated"))
        assert any(r["id"] == "real_rate_low" for r in matched2)

    def test_matching_is_deterministic(self):
        matrix = _matrix(fiscal=70.0, value=65.0, m2=9.0, pmi=51.0, real_rate=-0.5, real_status="calculated")
        assert [r["id"] for r in evaluate_rules(matrix)] == [r["id"] for r in evaluate_rules(matrix)]


class TestIndustryRanking:
    def test_ranking_counts_rule_hits(self):
        matched = [
            {"id": "a", "title": "规则A", "industries": [{"name": "银行", "reason": "r1", "boards": ["银行"]}]},
            {"id": "b", "title": "规则B", "industries": [{"name": "银行", "reason": "r2", "boards": ["银行"]},
                                                          {"name": "证券", "reason": "r3", "boards": ["证券"]}]},
        ]
        ranked = rank_industries(matched, [])
        assert ranked[0]["industry"] == "银行" and ranked[0]["score"] == 2
        assert any(item["industry"] == "证券" and item["score"] == 1 for item in ranked)

    def test_fund_flow_fuzzy_matched_and_honest_when_missing(self):
        matched = [{"id": "a", "title": "规则A", "industries": [
            {"name": "银行", "reason": "r1", "boards": ["银行"]},
            {"name": "软件", "reason": "r2", "boards": ["软件开发"]},
        ]}]
        flow = [{"sector": "银行", "flow": 12.5}]
        ranked = rank_industries(matched, flow)
        by_name = {item["industry"]: item for item in ranked}
        assert by_name["银行"]["fund_flow"] == 12.5
        assert by_name["软件"]["fund_flow_status"] == "unavailable"


class TestCandidatePool:
    def test_pool_sorted_by_market_cap_with_disclaimer(self, monkeypatch):
        frame = pd.DataFrame([
            {"代码": "600002", "名称": "小盘股", "最新价": 10.0, "流通市值": "50亿"},
            {"代码": "600001", "名称": "大盘股", "最新价": 20.0, "流通市值": "800亿"},
        ])

        class _FakeAK:
            @staticmethod
            def stock_board_industry_cons_em(symbol):
                return frame

        import sys, types
        monkeypatch.setitem(sys.modules, "akshare", _FakeAK)

        async def _gated(func, **kwargs):
            return func()

        monkeypatch.setattr("app.services.akshare_gate.gated_call", _gated)
        data = __import__("asyncio").run(get_candidate_pool("银行", 8))
        assert data["data_status"] == "realtime"
        assert data["candidates"][0]["code"] == "600001"  # 市值大的在前
        assert "不是投资建议" in data["disclaimer"]

    def test_pool_source_failure_degrades_honestly(self, monkeypatch):
        class _FakeAK:
            @staticmethod
            def stock_board_industry_cons_em(symbol):
                raise RuntimeError("数据源不可用")

        import sys, types
        monkeypatch.setitem(sys.modules, "akshare", _FakeAK)

        async def _gated(func, **kwargs):
            return func()

        monkeypatch.setattr("app.services.akshare_gate.gated_call", _gated)
        data = __import__("asyncio").run(get_candidate_pool("银行", 8))
        assert data["data_status"] == "unavailable"
        assert data["candidates"] == []
        assert "不是投资建议" in data["disclaimer"]


class TestFunnelAPI:
    def test_ranking_endpoint_shape(self, client, monkeypatch):
        async def _fake_matrix(force=False):
            return _matrix(fiscal=70.0, value=50.0, m2=9.0)

        async def _fake_flow():
            return []

        async def _fake_funnel():
            matrix = await _fake_matrix()
            matched = evaluate_rules(matrix)
            ranked = rank_industries(matched, [])
            return {"matrix_cell": matrix.get("matrix_cell"), "matrix_scores": {},
                    "matched_rules": matched, "rule_count": len(matched),
                    "industries": ranked, "data_status": "available",
                    "message": "", "disclaimer": macro_funnel.DISCLAIMER}

        monkeypatch.setattr("app.api.funnel.get_funnel_ranking", _fake_funnel)
        monkeypatch.setattr("app.services.macro_funnel.get_macro_matrix", _fake_matrix)
        monkeypatch.setattr("app.services.macro_funnel._fetch_fund_flow", _fake_flow)
        resp = client.get("/api/funnel/macro-industry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["industries"], "财政扩张矩阵应命中行业"
        assert any(item["industry"] == "建筑装饰" for item in data["industries"])
        assert "不是投资建议" in data["disclaimer"]

    def test_pool_endpoint(self, client, monkeypatch):
        async def _fake_pool(board, size=8):
            return {"board": board, "data_status": "realtime", "sort_factor": "流通市值降序",
                    "candidates": [{"code": "600001", "name": "x", "price": 1, "market_cap_text": "1亿"}],
                    "disclaimer": macro_funnel.DISCLAIMER}

        monkeypatch.setattr("app.api.funnel.get_candidate_pool", _fake_pool)
        resp = client.get("/api/funnel/candidate-pool", params={"board": "银行"})
        assert resp.status_code == 200
        assert resp.json()["candidates"][0]["code"] == "600001"

    def test_pool_requires_board(self, client):
        assert client.get("/api/funnel/candidate-pool").status_code == 422
