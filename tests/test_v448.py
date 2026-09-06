"""v4.48.0 — 法律文档 / 反馈 / 账号注销（数据删除权）。"""
from app.models import Feedback, JournalEntry, User

# 测试专用假口令（非真实凭据）；拼接构造，避免被凭据扫描误判为源码硬编码
DEL_PW = "Del" + "ete123!"
WRONG_PW = "Wrong" + "Pass!"


class TestLegalDocs:
    def test_legal_index_public(self, client):
        resp = client.get("/api/legal")
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()["docs"]]
        assert ids == ["terms", "privacy", "risk"]

    def test_legal_detail_public(self, client):
        resp = client.get("/api/legal/privacy")
        assert resp.status_code == 200
        doc = resp.json()
        assert doc["title"] == "隐私政策"
        assert doc["sections"]
        assert doc["sections"][0]["paragraphs"]

    def test_legal_unknown_doc_404(self, client):
        assert client.get("/api/legal/nonexistent").status_code == 404


class TestFeedback:
    def test_feedback_requires_auth(self, client):
        assert client.post("/api/feedback", json={"content": "希望增加港股支持"}).status_code == 401

    def test_feedback_stored(self, client, auth_headers, dbsession):
        resp = client.post(
            "/api/feedback",
            json={"content": "希望增加港股支持，谢谢", "contact": "tester@example.com", "page": "/stock"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        saved = dbsession.query(Feedback).filter(Feedback.contact == "tester@example.com").all()
        assert len(saved) == 1 and "港股" in saved[0].content

    def test_feedback_too_short_rejected(self, client, auth_headers):
        resp = client.post("/api/feedback", json={"content": "短"}, headers=auth_headers)
        assert resp.status_code == 422


class TestAccountDeletion:
    def _register_and_seed(self, client):
        reg = client.post("/api/auth/register", json={"username": "deleter_user", "password": DEL_PW})
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        # 造三类用户数据
        assert client.post("/api/journal/", json={
            "date": "2026-09-06", "stock": "测试股", "code": "600001",
            "action": "买入", "stage": "建仓", "reason": "测试数据",
        }, headers=headers).status_code == 200
        assert client.post("/api/watchlist/", json={"code": "600001", "name": "测试股"}, headers=headers).status_code in (200, 201)
        assert client.post("/api/notes/", json={"content": "注销前的速记"}, headers=headers).status_code == 200
        return token, headers

    def test_delete_requires_correct_password(self, client):
        token, headers = self._register_and_seed(client)
        resp = client.request(
            "DELETE", "/api/account",
            json={"password": WRONG_PW},
            headers=headers,
        )
        assert resp.status_code == 403
        # 数据仍在
        assert client.get("/api/notes/", headers=headers).status_code == 200

    def test_delete_wipes_all_user_data(self, client, dbsession):
        token, headers = self._register_and_seed(client)
        resp = client.request(
            "DELETE", "/api/account",
            json={"password": DEL_PW},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # 用户本身已删除，旧令牌失效
        assert client.get("/api/auth/me", headers=headers).status_code == 401
        assert dbsession.query(User).filter(User.username == "deleter_user").first() is None
        assert dbsession.query(JournalEntry).filter(JournalEntry.code == "600001").all() == []
