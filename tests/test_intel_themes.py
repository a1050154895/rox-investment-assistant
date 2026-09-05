"""情报主题主线：聚类、突发标记与用户关联度排序测试。"""
from datetime import datetime, timedelta

from app.services.intel_themes import build_themes, is_breaking, mark_breaking, rank_for_user


def _news(title, hours_ago, category="市场资讯", channels=None):
    return {
        "title": title,
        "category": category,
        "channels": channels or [],
        "published_at": (datetime.now() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M"),
        "source": "测试",
        "fact_or_view": "事实线索",
    }


class TestThemes:
    def test_cluster_by_keywords(self):
        news = [
            _news("美联储暗示年内降息节奏", 2, "货币政策"),
            _news("国债收益率下行提振成长股估值", 5),
            _news("半导体设备订单回暖", 3, "科技", ["半导体"]),
            _news("某公司公布年度业绩", 8),
        ]
        themes = build_themes(news)
        names = [t["name"] for t in themes]
        assert "利率与流动性" in names
        rates = next(t for t in themes if t["name"] == "利率与流动性")
        assert rates["count"] == 2
        assert rates["timeline"][0]["published_at"] <= rates["timeline"][-1]["published_at"]
        assert rates["verify_question"]

    def test_breaking_flag_and_pinning(self):
        news = [_news("央行突发降息十个基点", 3), _news("常规市场收盘综述", 4), _news("很早之前的降息新闻", 200)]
        assert is_breaking(news[0]) is True
        assert is_breaking(news[1]) is False
        assert is_breaking(news[2]) is False  # 超出时间窗口不算突发
        marked = mark_breaking(news)
        assert marked[0]["title"].startswith("央行突发")
        assert all(n["is_breaking"] is False for n in marked[1:])

    def test_rank_for_user_prioritizes_research(self):
        news = [_news("贵州茅台发布业绩预告", 3), _news("无关行业的常规资讯", 2)]
        themes = build_themes([news[0]])
        ranked = rank_for_user(themes, mark_breaking(news), cards=[{"stock": "贵州茅台"}])
        assert ranked["news"][0]["title"].startswith("贵州茅台")
        assert "贵州茅台" in ranked["news"][0]["research_relevant"]
        assert ranked["sort_rule"]

    def test_policy_topics_attached(self):
        news = [_news("促消费政策细则落地", 4, "政策", ["食品饮料"])]
        policy = [{"topic": "扩内需与消费", "affected": ["食品饮料"]}]
        themes = build_themes(news, policy)
        assert any("扩内需与消费" in t.get("policy_topics", []) for t in themes)


class TestFeedAPI:
    def test_feed_requires_auth(self, client):
        assert client.get("/api/intelligence/feed").status_code == 401

    def test_brief_contains_themes(self, client):
        data = client.get("/api/intelligence/brief").json()
        assert isinstance(data["themes"], list)
        # 数据可信契约：离线/无数据源时资讯为空、状态如实标注 unavailable，
        # 不再回退到手写假资讯（主题引擎的正向覆盖见 TestThemeEngine）。
        if data.get("news_status") == "unavailable":
            assert data["news"] == []
            assert data["themes"] == []
        else:
            assert data["themes"]
        for theme in data["themes"]:
            assert "timeline" in theme and "verify_question" in theme
        for item in data["news"]:
            assert "is_breaking" in item

    def test_feed_ranked_by_user_cards(self, client, auth_headers):
        client.post("/api/research/", json={"title": "消费研究", "stock": "食品饮料行业观察"}, headers=auth_headers)
        data = client.get("/api/intelligence/feed", headers=auth_headers).json()
        assert "sort_rule" in data
        assert isinstance(data["matched_targets"], list)
