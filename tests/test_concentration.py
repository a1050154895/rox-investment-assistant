"""成交额集中度温度计测试。"""
from app.services.market_concentration import compute_concentration


class TestConcentration:
    def test_uniform_amounts_give_expected_share(self):
        # 1000 只等额成交 → 前5%(50只) 占 5%
        result = compute_concentration([1e8] * 1000)
        assert result["top5_pct"] == 5.0
        assert result["top10_pct"] == 10.0
        assert result["stock_count"] == 1000

    def test_highly_concentrated(self):
        # 前50只占绝对大头
        amounts = [1e10] * 50 + [1e6] * 950
        result = compute_concentration(amounts)
        assert result["top5_pct"] > 95

    def test_insufficient_stocks_returns_none(self):
        assert compute_concentration([1e8] * 50) is None

    def test_zero_amounts_filtered(self):
        # 0/负值被过滤，不进入分母
        amounts = [1e8] * 999 + [0, -5]
        result = compute_concentration(amounts)
        assert result["stock_count"] == 999

    def test_api_requires_auth(self, client):
        assert client.get("/api/intelligence/concentration").status_code == 401


class TestResearchTemplates:
    def test_list_templates(self, client):
        data = client.get("/api/research/templates").json()
        ids = {t["id"] for t in data["templates"]}
        assert {"serenity_chain", "discipline_guard"} <= ids

    def test_template_seed_has_no_conclusion(self, client):
        data = client.get("/api/research/templates/serenity_chain").json()
        seed = data["seed"]
        assert seed["question"] and seed["hypothesis"] and seed["invalidation"]
        assert "证伪" in seed["invalidation"]  # 模板给的是问法和失效条件，不是结论
        assert client.get("/api/research/templates/notexist").status_code == 404
