"""ROX 核心 API 冒烟测试。"""
import pytest


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "3.7.0"
        assert "key_source" in data

    def test_ready_ok(self, client):
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "checks" in data


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


class TestFundamentals:
    def test_dcf_available(self, client):
        resp = client.get("/api/fundamentals/600519/dcf", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("available", "unavailable")
        if data["status"] == "available":
            assert data["fair_price"] is not None
            assert "assumptions" in data

    def test_comps_structure(self, client):
        resp = client.get("/api/fundamentals/600519/comps", timeout=30)
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
        resp = client.get("/api/dashboard/overview", timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        assert "macro_compass" in data


class TestReview:
    def test_daily(self, client):
        resp = client.get("/api/review/daily", timeout=30)
        assert resp.status_code in (200, 503)


class TestDiscipline:
    def test_defaults(self, client):
        resp = client.get("/api/discipline/defaults")
        assert resp.status_code == 200
        data = resp.json()
        assert "profile" in data
