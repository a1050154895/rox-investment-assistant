"""AI 三层模式与 BYOK 加密存储测试。"""
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret


class TestCrypto:
    def test_roundtrip(self):
        token = encrypt_secret("sk-test-123456")
        assert token.startswith("enc:")
        assert "sk-test-123456" not in token
        assert decrypt_secret(token) == "sk-test-123456"

    def test_plaintext_backward_compatible(self):
        assert decrypt_secret("legacy-plaintext") == "legacy-plaintext"

    def test_empty_and_double_encrypt(self):
        assert encrypt_secret("") == ""
        once = encrypt_secret("abc")
        assert encrypt_secret(once) == once

    def test_mask(self):
        assert mask_secret(encrypt_secret("sk-verylongkey123")) .startswith("sk-v")
        assert mask_secret("") is None


class TestAIModes:
    def test_default_mode_is_platform(self, client, auth_headers):
        data = client.get("/api/settings/", headers=auth_headers).json()
        assert data["ai_mode"] == "platform"
        assert "ai_modes" in data

    def test_invalid_mode_rejected(self, client, auth_headers):
        resp = client.put("/api/settings/", json={"ai_mode": "magic"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_off_mode_disables_ai(self, client, auth_headers):
        client.put("/api/settings/", json={"ai_mode": "off"}, headers=auth_headers)
        status = client.get("/api/ai/status", headers=auth_headers).json()
        assert status["mode"] == "off"
        assert status["configured"] is False
        chat = client.post("/api/ai/chat", json={"question": "测试"}, headers=auth_headers)
        assert chat.status_code == 503
        assert chat.json()["detail"]["code"] == "AI_DISABLED"

    def test_byok_key_encrypted_and_masked(self, client, auth_headers):
        client.put("/api/settings/", json={
            "ai_mode": "byok", "ai_api_key": "sk-mybyokkey-987654321",
            "ai_api_url": "https://api.deepseek.com", "ai_model": "deepseek-chat",
        }, headers=auth_headers)
        settings = client.get("/api/settings/", headers=auth_headers).json()
        assert settings["ai_mode"] == "byok"
        assert settings["ai_key_configured"] is True
        assert "sk-mybyokkey-987654321" not in str(settings)
        assert settings["ai_key_masked"].startswith("sk-m")

        status = client.get("/api/ai/status", headers=auth_headers).json()
        assert status["mode"] == "byok"
        assert status["configured"] is True
        assert status["source"] == "user_settings"

    def test_delete_ai_key(self, client, auth_headers):
        client.put("/api/settings/", json={"ai_mode": "byok", "ai_api_key": "sk-to-delete"}, headers=auth_headers)
        resp = client.delete("/api/settings/ai-key", headers=auth_headers)
        assert resp.status_code == 200
        settings = client.get("/api/settings/", headers=auth_headers).json()
        assert settings["ai_key_masked"] is None
        status = client.get("/api/ai/status", headers=auth_headers).json()
        assert status["configured"] is False

    def test_status_note_present(self, client, auth_headers):
        status = client.get("/api/ai/status", headers=auth_headers).json()
        assert "模型辅助" in status["note"]
