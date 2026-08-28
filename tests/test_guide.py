"""教程 API 与路由覆盖测试：确保每个页面都有教程。"""
import re


def test_guide_returns_all_sections(client):
    resp = client.get("/api/guide/")
    assert resp.status_code == 200
    data = resp.json()
    assert "onboarding_steps" in data
    assert "features" in data
    assert "faq" in data
    assert "glossary" in data
    assert "shortcuts" in data


def test_guide_onboarding_steps_complete(client):
    resp = client.get("/api/guide/")
    steps = resp.json()["onboarding_steps"]
    assert len(steps) >= 8
    for s in steps:
        assert "step" in s
        assert "title" in s
        assert "detail" in s
        assert len(s["title"]) > 0
        assert len(s["detail"]) > 20


def test_guide_features_cover_all_nav_routes(client):
    """确保每个导航路由都有对应的功能说明。"""
    resp = client.get("/api/guide/")
    features = resp.json()["features"]
    feature_routes = {f.get("route") for f in features if f.get("route")}

    # 从 shell.html 提取所有 data-route
    with open("templates/shell.html", "r") as f:
        html = f.read()
    nav_routes = set(re.findall(r'data-route="([^"]+)"', html))

    # 每个导航路由（排除 /guide 本身）都应该有对应功能说明
    nav_routes.discard("/guide")
    missing = nav_routes - feature_routes
    assert not missing, f"以下路由缺少功能说明: {missing}"


def test_guide_faq_not_empty(client):
    resp = client.get("/api/guide/")
    faq = resp.json()["faq"]
    assert len(faq) >= 5
    for f in faq:
        assert "q" in f and "a" in f
        assert len(f["a"]) > 20


def test_guide_glossary_has_key_terms(client):
    resp = client.get("/api/guide/")
    glossary = resp.json()["glossary"]
    terms = {g["term"] for g in glossary}
    assert "ATR" in terms
    assert "研究卡" in terms
    assert "334 纪律" in terms
    assert "反证" in terms
