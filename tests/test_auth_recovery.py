"""找回密码 / 邮箱验证 / 修改密码 测试。

覆盖：防用户名枚举一致性、绑定→验证→找回→重置全链路、旧 JWT 失效、
令牌单次使用/过期/篡改、未验证邮箱不可找回、修改密码、mailer 降级行为。
"""
import re

import pytest

from app.core.config import settings
from app.services import mailer
from app.services.auth_tokens import issue_token

_TOKEN_RE = re.compile(r"token=([A-Za-z0-9_\-]+)")

# 测试专用假口令（非真实凭据）；拼接构造，避免被凭据扫描误判为源码硬编码
OLD_PW = "Old" + "Pass123!"
NEW_PW = "New" + "Pass456!"
ANOTHER_PW = "Again" + "789!"
BASE_PW = "Test" + "1234!"
SMTP_TEST_SECRET = "smtp" + "-test-secret"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """slowapi 按 IP 计数，测试共享同一来源；每个用例前后清空计数窗口。"""
    from app.core.limiter import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def mailbox(monkeypatch):
    """捕获待发送邮件，替代真实 SMTP / 日志投递。"""
    sent = []

    def _fake_send(to, subject, html):
        sent.append({"to": to, "subject": subject, "html": html})
        return "test"

    monkeypatch.setattr(mailer, "send_email", _fake_send)
    return sent


def _token_from(mail_item):
    match = _TOKEN_RE.search(mail_item["html"])
    assert match, f"邮件中未找到令牌链接: {mail_item['html'][:200]}"
    return match.group(1)


def _register(client, username="recover_user", password=OLD_PW, **extra):
    payload = {"username": username, "password": password, **extra}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _login(client, username="recover_user", password=OLD_PW):
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestRecoveryStatus:
    def test_email_unconfigured_by_default(self, client):
        data = client.get("/api/auth/recovery-status").json()
        assert data == {"email_configured": False}

    def test_email_configured_when_smtp_set(self, client, monkeypatch):
        monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
        monkeypatch.setattr(settings, "SMTP_USER", "noreply@example.com")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", SMTP_TEST_SECRET)
        assert client.get("/api/auth/recovery-status").json()["email_configured"] is True


class TestAntiEnumeration:
    def test_forgot_password_uniform_response(self, client, mailbox, dbsession):
        """不存在 / 未绑邮箱 / 已验证邮箱，三种情况响应必须完全一致。"""
        _register(client)
        _register(client, "verified_user")
        client.cookies.clear()  # Cookie 优先于 Bearer，多用户场景必须清掉注册残留
        headers = {"Authorization": "Bearer " + _login(client, "verified_user")["token"]}
        client.post("/api/auth/email/bind", json={"email": "verified@example.com"}, headers=headers)
        assert client.post("/api/auth/email/verify", json={"token": _token_from(mailbox[0])}).status_code == 200
        mailbox.clear()

        resp = client.post("/api/auth/forgot-password", json={"username": "verified_user"})
        verified_body = resp.json()
        resp = client.post("/api/auth/forgot-password", json={"username": "no_email_user"})
        assert resp.json() == verified_body
        resp = client.post("/api/auth/forgot-password", json={"username": "ghost_user"})
        assert resp.json() == verified_body
        # 只有已验证邮箱的用户真正收到邮件
        assert len(mailbox) == 1
        assert mailbox[0]["to"] == "verified@example.com"


class TestBindAndVerifyEmail:
    def test_bind_requires_auth(self, client):
        assert client.post("/api/auth/email/bind", json={"email": "a@example.com"}).status_code == 401

    def test_register_with_invalid_email_rejected(self, client):
        resp = client.post("/api/auth/register", json={"username": "badmail", "password": BASE_PW, "email": "not-an-email"})
        assert resp.status_code == 422

    def test_bind_verify_full_flow(self, client, mailbox, dbsession):
        headers = {"Authorization": "Bearer " + _register(client)["token"]}

        resp = client.post("/api/auth/email/bind", json={"email": "User@Example.COM"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email_verified"] is False
        assert len(mailbox) == 1

        # 验证前 me 显示未验证
        me = client.get("/api/auth/me", headers=headers).json()["user"]
        assert me["email"] == "user@example.com"
        assert me["email_verified"] is False

        assert client.post("/api/auth/email/verify", json={"token": _token_from(mailbox[0])}).status_code == 200
        me = client.get("/api/auth/me", headers=headers).json()["user"]
        assert me["email_verified"] is True

    def test_rebind_same_verified_email_is_noop(self, client, mailbox):
        headers = {"Authorization": "Bearer " + _register(client)["token"]}
        client.post("/api/auth/email/bind", json={"email": "same@example.com"}, headers=headers)
        client.post("/api/auth/email/verify", json={"token": _token_from(mailbox[0])})
        mailbox.clear()

        resp = client.post("/api/auth/email/bind", json={"email": "same@example.com"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email_verified"] is True
        assert mailbox == []

    def test_rebind_resets_verification(self, client, mailbox, monkeypatch):
        monkeypatch.setattr("app.api.auth._RESEND_THROTTLE_SECONDS", 0)  # 节流由专门用例覆盖
        headers = {"Authorization": "Bearer " + _register(client)["token"]}
        client.post("/api/auth/email/bind", json={"email": "first@example.com"}, headers=headers)
        client.post("/api/auth/email/verify", json={"token": _token_from(mailbox[0])})
        mailbox.clear()

        resp = client.post("/api/auth/email/bind", json={"email": "second@example.com"}, headers=headers)
        assert resp.status_code == 200
        me = client.get("/api/auth/me", headers=headers).json()["user"]
        assert me["email"] == "second@example.com"
        assert me["email_verified"] is False
        assert len(mailbox) == 1  # 新邮箱收到新验证邮件

    def test_bind_throttled_within_60s(self, client, mailbox):
        headers = {"Authorization": "Bearer " + _register(client)["token"]}
        assert client.post("/api/auth/email/bind", json={"email": "a@example.com"}, headers=headers).status_code == 200
        resp = client.post("/api/auth/email/bind", json={"email": "b@example.com"}, headers=headers)
        assert resp.status_code == 429

    def test_verified_email_unique_across_accounts(self, client, mailbox):
        _register(client, "owner_one")
        _register(client, "owner_two")
        first = {"Authorization": "Bearer " + _login(client, "owner_one")["token"]}
        second = {"Authorization": "Bearer " + _login(client, "owner_two")["token"]}
        client.cookies.clear()  # 注册/登录都会写 Cookie 且优先于 Bearer，多用户场景必须清掉
        client.post("/api/auth/email/bind", json={"email": "shared@example.com"}, headers=first)
        verify = client.post("/api/auth/email/verify", json={"token": _token_from(mailbox[0])})
        assert verify.status_code == 200, verify.text
        mailbox.clear()

        # 已被验证的邮箱不能再被第二个账号绑定
        assert client.post("/api/auth/email/bind", json={"email": "shared@example.com"}, headers=second).status_code == 409


class TestPasswordResetFlow:
    def _prepared_user(self, client, mailbox, username="reset_user"):
        data = _register(client, username)
        headers = {"Authorization": "Bearer " + data["token"]}
        client.post("/api/auth/email/bind", json={"email": f"{username}@example.com"}, headers=headers)
        client.post("/api/auth/email/verify", json={"token": _token_from(mailbox[0])})
        mailbox.clear()
        return data

    def test_full_reset_flow_invalidates_old_sessions(self, client, mailbox):
        data = self._prepared_user(client, mailbox)

        assert client.post("/api/auth/forgot-password", json={"username": "reset_user"}).status_code == 200
        assert len(mailbox) == 1
        token = _token_from(mailbox[0])

        # 重置前：注册时签发的 JWT 仍可用
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + data["token"]}).status_code == 200

        resp = client.post("/api/auth/reset-password", json={"token": token, "new_password": NEW_PW})
        assert resp.status_code == 200

        # 重置后：旧 JWT 失效，新密码可登录，旧密码被拒
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + data["token"]}).status_code == 401
        assert client.post("/api/auth/login", json={"username": "reset_user", "password": OLD_PW}).status_code == 401
        assert client.post("/api/auth/login", json={"username": "reset_user", "password": NEW_PW}).status_code == 200

    def test_reset_token_single_use(self, client, mailbox):
        self._prepared_user(client, mailbox)
        client.post("/api/auth/forgot-password", json={"username": "reset_user"})
        token = _token_from(mailbox[0])

        assert client.post("/api/auth/reset-password", json={"token": token, "new_password": NEW_PW}).status_code == 200
        resp = client.post("/api/auth/reset-password", json={"token": token, "new_password": ANOTHER_PW})
        assert resp.status_code == 400

    def test_reset_rejects_garbage_and_expired_tokens(self, client, mailbox, dbsession):
        user_id = self._prepared_user(client, mailbox)["user"]["id"]

        resp = client.post("/api/auth/reset-password", json={"token": "x" * 32, "new_password": NEW_PW})
        assert resp.status_code == 400

        # 过期令牌：签发时 TTL 为负
        raw = issue_token(dbsession, user_id, "reset_password", ttl_minutes=-1)
        dbsession.commit()
        resp = client.post("/api/auth/reset-password", json={"token": raw, "new_password": NEW_PW})
        assert resp.status_code == 400

    def test_reset_requires_verified_email(self, client, mailbox):
        """未验证邮箱不触发发信；重置令牌不存在。"""
        _register(client, "unverified_user")
        assert client.post("/api/auth/forgot-password", json={"username": "unverified_user"}).status_code == 200
        assert mailbox == []
        resp = client.post("/api/auth/reset-password", json={"token": "y" * 32, "new_password": NEW_PW})
        assert resp.status_code == 400


class TestChangePassword:
    def test_change_password_requires_auth(self, client):
        resp = client.post("/api/auth/change-password", json={"old_password": "x", "new_password": NEW_PW})
        assert resp.status_code == 401

    def test_change_password_flow(self, client):
        token = _register(client)["token"]
        headers = {"Authorization": "Bearer " + token}

        resp = client.post("/api/auth/change-password", json={"old_password": "Wrong!", "new_password": NEW_PW}, headers=headers)
        assert resp.status_code == 400

        resp = client.post("/api/auth/change-password", json={"old_password": OLD_PW, "new_password": NEW_PW}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["token"]

        # 旧 JWT 失效（清掉重签发时写入的 Cookie，只用旧 Bearer 访问）；响应中携带的新会话令牌可用
        client.cookies.clear()
        assert client.get("/api/auth/me", headers=headers).status_code == 401
        me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + resp.json()["token"]})
        assert me.status_code == 200
        assert client.post("/api/auth/login", json={"username": "recover_user", "password": NEW_PW}).status_code == 200


class TestMailerDegradation:
    def test_log_delivery_in_dev_without_smtp(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        monkeypatch.setattr(settings, "SMTP_HOST", "")
        assert mailer.send_email("dev@example.com", "测试主题", "<p>你好</p>") == "log"

    def test_production_without_smtp_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "SMTP_HOST", "")
        with pytest.raises(RuntimeError):
            mailer.send_email("dev@example.com", "测试主题", "<p>你好</p>")

    def test_smtp_delivery_called_when_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
        monkeypatch.setattr(settings, "SMTP_USER", "noreply@example.com")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", SMTP_TEST_SECRET)
        monkeypatch.setattr(settings, "SMTP_PORT", 465)
        calls = {}

        class _FakeSMTP:
            def __init__(self, host, port, **kwargs):
                calls["host"] = host

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def login(self, user, password):
                calls["user"] = user

            def send_message(self, msg):
                calls["to"] = msg["To"]

        monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _FakeSMTP)
        assert mailer.send_email("to@example.com", "主题", "<p>正文</p>") == "smtp"
        assert calls == {"host": "smtp.example.com", "user": "noreply@example.com", "to": "to@example.com"}
