"""ROX 核心 API 冒烟测试。"""
import pytest


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "4.6.0"
        assert "key_source" in data

    def test_ready_ok(self, client):
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "checks" in data


class TestSpa:
    def test_index_renders_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_fallback_route_renders_html(self, client):
        resp = client.get("/stock")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")


class TestAuth:
    def test_register_new_user(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "test_vz92",
            "password": "Secret123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["token"]) > 20

    def test_register_duplicate_rejected(self, client):
        client.post("/api/auth/register", json={"username": "dup_usr", "password": "Pass12345!"})
        resp = client.post("/api/auth/register", json={"username": "dup_usr", "password": "Pass12345!"})
        assert resp.status_code == 409

    def test_login_invalid_rejected(self, client):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "Wrong"})
        assert resp.status_code == 401

    def test_login_valid_returns_token(self, auth_token):
        assert auth_token["token"]
        assert len(auth_token["token"]) > 20

    def test_me_requires_auth(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["user"]["username"] == "pytest_user"

    def test_me_unauthorized(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_cookie_auth_flow(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "cookie_user",
            "password": "Cookie123!",
        })
        assert resp.status_code == 200
        assert "rox_token" in resp.cookies

        # 不携带 Authorization 头，仅靠 HttpOnly Cookie 也应能通过鉴权
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["username"] == "cookie_user"

        # 登出后 Cookie 清除，再次访问应 401
        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/auth/me").status_code == 401


class TestFundamentals:
    def test_dcf_available(self, client):
        resp = client.get("/api/fundamentals/600519/dcf")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("available", "unavailable")
        if data["status"] == "available":
            assert data["fair_price"] is not None
            assert "assumptions" in data

    def test_comps_structure(self, client):
        resp = client.get("/api/fundamentals/600519/comps")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestPortfolio:
    def test_empty_portfolio(self, client, auth_headers):
        resp = client.get("/api/portfolio/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["summary"]["count"] == 0

    def test_add_and_list(self, client, auth_headers):
        add = client.post("/api/portfolio/", json={
            "code": "600519", "name": "贵州茅台",
            "shares": 100, "cost_price": 1320.00, "date": "2026-08-09",
        }, headers=auth_headers)
        assert add.status_code == 200
        assert add.json()["success"] is True

        lst = client.get("/api/portfolio/", headers=auth_headers)
        assert lst.json()["summary"]["count"] == 1
        assert lst.json()["positions"][0]["code"] == "600519"

    def test_delete_position(self, client, auth_headers):
        add = client.post("/api/portfolio/", json={
            "code": "000858", "name": "五粮液",
            "shares": 50, "cost_price": 112.00, "date": "2026-08-09",
        }, headers=auth_headers)
        pid = add.json()["position"]["id"]

        # delete
        resp = client.delete(f"/api/portfolio/{pid}", headers=auth_headers)
        assert resp.status_code == 200

        # verify empty
        lst = client.get("/api/portfolio/", headers=auth_headers)
        assert lst.json()["summary"]["count"] == 0


class TestJournal:
    def test_list_decisions(self, client, auth_headers):
        resp = client.get("/api/journal/", headers=auth_headers)
        assert resp.status_code == 200
        assert "decisions" in resp.json()

    def test_create_decision(self, client, auth_headers):
        resp = client.post("/api/journal/", json={
            "stock": "贵州茅台", "code": "600519", "action": "买入",
            "stage": "试仓30%", "cycle_stage": "积累",
            "contradiction_intensity": 65, "value_realization": 70,
            "consistency_score": 80, "reason": "测试决策",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"]["stock"] == "贵州茅台"

    def test_update_decision_full_fields(self, client, auth_headers):
        """PUT 全字段编辑：修改决策本身的字段（非仅结果追踪）。"""
        # 先创建
        create = client.post("/api/journal/", json={
            "stock": "测试股", "code": "000001", "action": "买入",
            "stage": "试仓30%", "cycle_stage": "积累",
            "contradiction_intensity": 50, "value_realization": 50,
            "consistency_score": 50, "reason": "原始理由",
        }, headers=auth_headers)
        assert create.status_code == 200
        did = create.json()["id"]

        # 全字段编辑
        resp = client.put(f"/api/journal/{did}", json={
            "stock": "修改后的股", "action": "卖出", "reason": "修正理由",
            "consistency_score": 85, "result": "盈", "result_pct": 12.5,
        }, headers=auth_headers)
        assert resp.status_code == 200
        d = resp.json()["decision"]
        assert d["stock"] == "修改后的股"
        assert d["action"] == "卖出"
        assert d["reason"] == "修正理由"
        assert d["consistency_score"] == 85
        assert d["result"] == "盈"
        assert d["result_pct"] == 12.5

    def test_delete_decision(self, client, auth_headers):
        """DELETE 删除决策记录。"""
        create = client.post("/api/journal/", json={
            "stock": "待删除", "code": "000002", "action": "持有",
            "stage": "确认30%", "cycle_stage": "流转",
            "contradiction_intensity": 40, "value_realization": 40,
            "consistency_score": 40, "reason": "测试删除",
        }, headers=auth_headers)
        assert create.status_code == 200
        did = create.json()["id"]

        resp = client.delete(f"/api/journal/{did}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # 确认已删除
        get = client.get(f"/api/journal/{did}", headers=auth_headers)
        assert get.status_code == 404

    def test_decision_context_snapshot(self, client, auth_headers):
        """创建决策时自动快照宏观/周期/矛盾上下文。"""
        create = client.post("/api/journal/", json={
            "stock": "贵州茅台", "code": "600519", "action": "买入",
            "stage": "试仓30%", "cycle_stage": "积累",
            "contradiction_intensity": 60, "value_realization": 60,
            "consistency_score": 70, "reason": "上下文快照测试",
        }, headers=auth_headers)
        assert create.status_code == 200
        did = create.json()["id"]

        detail = client.get(f"/api/journal/{did}", headers=auth_headers)
        assert detail.status_code == 200
        ctx = detail.json().get("context")
        assert ctx is not None
        assert ctx["cycle_stage"] in ("积累", "集中", "流转", "分配", "再生产", "未评估")
        assert "primary_contradiction" in ctx


class TestScreener:
    def test_presets(self, client):
        resp = client.get("/api/screener/presets")
        assert resp.status_code == 200
        assert "presets" in resp.json()


class TestBacktest:
    def test_strategies(self, client):
        resp = client.get("/api/backtest/strategies")
        assert resp.status_code == 200
        assert len(resp.json()["strategies"]) >= 1

    def test_stocks_list(self, client):
        resp = client.get("/api/backtest/stocks")
        assert resp.status_code == 200
        assert len(resp.json()["stocks"]) >= 10


class TestDashboard:
    def test_overview(self, client):
        resp = client.get("/api/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "macro_compass" in data


class TestReview:
    def test_daily(self, client):
        resp = client.get("/api/review/daily")
        assert resp.status_code in (200, 503)


class TestDiscipline:
    def test_defaults(self, client):
        resp = client.get("/api/discipline/defaults")
        assert resp.status_code == 200
        data = resp.json()
        assert "profile" in data


class TestWatchlist:
    def test_empty_watchlist(self, client, auth_headers):
        resp = client.get("/api/watchlist/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_add_and_remove(self, client, auth_headers):
        add = client.post("/api/watchlist/", json={
            "code": "600519", "name": "贵州茅台",
        }, headers=auth_headers)
        assert add.status_code == 200
        assert add.json()["success"] is True

        lst = client.get("/api/watchlist/", headers=auth_headers)
        assert lst.json()["count"] == 1
        wid = lst.json()["watchlist"][0]["id"]

        # 重复添加应不增加数量
        dup = client.post("/api/watchlist/", json={
            "code": "600519", "name": "贵州茅台",
        }, headers=auth_headers)
        assert dup.json()["exists"] is True
        assert client.get("/api/watchlist/", headers=auth_headers).json()["count"] == 1

        # 删除
        resp = client.delete(f"/api/watchlist/{wid}", headers=auth_headers)
        assert resp.status_code == 200
        assert client.get("/api/watchlist/", headers=auth_headers).json()["count"] == 0

    def test_requires_auth(self, client):
        resp = client.get("/api/watchlist/")
        assert resp.status_code == 401


class TestPortfolioUpdate:
    def test_update_position(self, client, auth_headers):
        add = client.post("/api/portfolio/", json={
            "code": "600519", "name": "贵州茅台",
            "shares": 100, "cost_price": 1320.00, "date": "2026-08-09",
        }, headers=auth_headers)
        pid = add.json()["position"]["id"]

        upd = client.put(f"/api/portfolio/{pid}", json={
            "shares": 200, "cost_price": 1400.00,
        }, headers=auth_headers)
        assert upd.status_code == 200
        data = upd.json()["position"]
        assert data["shares"] == 200
        assert data["cost_price"] == 1400.0

    def test_update_nonexistent(self, client, auth_headers):
        resp = client.put("/api/portfolio/9999", json={"shares": 10}, headers=auth_headers)
        assert resp.status_code == 404


class TestAlertUpdate:
    def test_toggle_alert(self, client, auth_headers):
        add = client.post("/api/alerts/", json={
            "code": "600519", "name": "贵州茅台",
            "target_price": 1500.00, "direction": "above",
        }, headers=auth_headers)
        aid = add.json()["alert"]["id"]

        # 暂停
        pause = client.put(f"/api/alerts/{aid}", json={"active": False}, headers=auth_headers)
        assert pause.status_code == 200
        assert pause.json()["alert"]["active"] is False

        # 重新激活应重置触发状态
        reactivate = client.put(f"/api/alerts/{aid}", json={"active": True}, headers=auth_headers)
        assert reactivate.json()["alert"]["active"] is True
        assert reactivate.json()["alert"]["triggered"] is False

    def test_update_nonexistent(self, client, auth_headers):
        resp = client.put("/api/alerts/9999", json={"active": False}, headers=auth_headers)
        assert resp.status_code == 404


class TestUserStats:
    def test_stats_empty(self, client, auth_headers):
        resp = client.get("/api/dashboard/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["journal"]["total"] == 0
        assert data["portfolio"]["count"] == 0
        assert data["alerts"]["total"] == 0
        assert data["watchlist"]["count"] == 0

    def test_stats_with_data(self, client, auth_headers):
        # 添加决策
        client.post("/api/journal/", json={
            "stock": "贵州茅台", "code": "600519", "action": "买入",
            "stage": "试仓30%", "cycle_stage": "积累",
            "contradiction_intensity": 65, "value_realization": 70,
            "consistency_score": 80, "reason": "测试",
        }, headers=auth_headers)
        # 添加持仓
        client.post("/api/portfolio/", json={
            "code": "600519", "name": "贵州茅台",
            "shares": 100, "cost_price": 1320.00, "date": "2026-08-09",
        }, headers=auth_headers)
        # 添加预警
        client.post("/api/alerts/", json={
            "code": "600519", "name": "贵州茅台",
            "target_price": 1500.00, "direction": "above",
        }, headers=auth_headers)
        # 添加自选
        client.post("/api/watchlist/", json={
            "code": "600519", "name": "贵州茅台",
        }, headers=auth_headers)

        resp = client.get("/api/dashboard/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["journal"]["total"] == 1
        assert data["portfolio"]["count"] == 1
        assert data["alerts"]["total"] == 1
        assert data["watchlist"]["count"] == 1

    def test_stats_requires_auth(self, client):
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 401


class TestQuoteCache:
    def test_cache_set_get_and_clear(self):
        from app.services import tencent_data as td
        td.clear_quote_cache()
        td._cache_set("q:test", {"price": 100})
        assert td._cache_get("q:test") == {"price": 100}
        td.clear_quote_cache()
        assert td._cache_get("q:test") is None

    def test_cache_ttl_expiry(self):
        from app.services import tencent_data as td
        td.clear_quote_cache()
        td._cache_set("q:ttl", {"price": 1})
        assert td._cache_get("q:ttl") is not None
        # 把时间戳拨到 TTL 之外，模拟过期
        ts, value = td._QUOTE_CACHE["q:ttl"]
        td._QUOTE_CACHE["q:ttl"] = (ts - td._QUOTE_CACHE_TTL - 1, value)
        assert td._cache_get("q:ttl") is None


class TestExport:
    def test_backup_includes_user_data(self, client, auth_headers):
        client.post("/api/journal/", json={
            "stock": "贵州茅台", "code": "600519", "action": "买入",
            "stage": "试仓30%", "cycle_stage": "积累",
            "contradiction_intensity": 65, "value_realization": 70,
            "consistency_score": 80, "reason": "备份测试",
        }, headers=auth_headers)
        client.post("/api/watchlist/", json={"code": "600519", "name": "贵州茅台"}, headers=auth_headers)

        resp = client.get("/api/export/backup", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
        assert "exported_at" in data
        assert len(data["journal"]) == 1
        assert data["journal"][0]["code"] == "600519"
        assert len(data["watchlist"]) == 1
        assert "settings" in data
        assert "positions" in data

    def test_report_generates_markdown(self, client, auth_headers):
        client.post("/api/journal/", json={
            "stock": "贵州茅台", "code": "600519", "action": "买入",
            "stage": "试仓30%", "cycle_stage": "积累",
            "contradiction_intensity": 65, "value_realization": 70,
            "consistency_score": 80, "reason": "报告测试",
        }, headers=auth_headers)

        resp = client.get("/api/export/report", headers=auth_headers)
        assert resp.status_code == 200
        text = resp.text
        assert "# ROX 研究报告" in text
        assert "决策复盘" in text
        assert "600519" in text
