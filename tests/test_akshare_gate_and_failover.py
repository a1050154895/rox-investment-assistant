"""AKShare 限流门与 BYOK failover 测试。"""
import asyncio

from app.services.ai_service import chat_with_fallback, resolve_fallback_config
from app.services.akshare_gate import RateGate, gated_call


class TestRateGate:
    def test_first_call_no_wait(self):
        gate = RateGate(min_interval=0.25)
        assert gate._wait_seconds() == 0.0

    def test_second_call_waits(self):
        t = {"now": 0.0}
        gate = RateGate(min_interval=0.25, clock=lambda: t["now"])
        gate._wait_seconds()
        t["now"] = 0.1
        wait = gate._wait_seconds()
        assert 0 < wait <= 0.25

    def test_after_interval_no_wait(self):
        t = {"now": 0.0}
        gate = RateGate(min_interval=0.25, clock=lambda: t["now"])
        gate._wait_seconds()
        t["now"] = 1.0
        assert gate._wait_seconds() == 0.0

    def test_gated_call_runs_and_retries(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("限流")
            return "ok"

        async def run():
            sleeps = []

            async def fake_sleep(s):
                sleeps.append(s)

            return await gated_call(flaky, retries=1, sleep=fake_sleep), sleeps

        result, sleeps = asyncio.run(run())
        assert result == "ok"
        assert calls["n"] == 2
        assert sleeps == [0.8]


class TestByokFailover:
    def test_fallback_only_in_byok_mode(self):
        platform = {"ai_mode": "platform", "ai_fallback_url": "https://x", "ai_fallback_key": "k"}
        assert resolve_fallback_config(platform) is None
        cfg = resolve_fallback_config({
            "ai_mode": "byok", "ai_fallback_url": "https://x.com/",
            "ai_fallback_key": "k", "ai_fallback_model": "m",
        })
        assert cfg == {"base": "https://x.com", "key": "k", "model": "m", "mode": "byok"}

    def test_fallback_requires_url_and_key(self):
        no_url = {"ai_mode": "byok", "ai_fallback_url": "", "ai_fallback_key": "k"}
        no_key = {"ai_mode": "byok", "ai_fallback_url": "https://x", "ai_fallback_key": ""}
        assert resolve_fallback_config(no_url) is None
        assert resolve_fallback_config(no_key) is None

    def test_chat_falls_back_on_primary_failure(self):
        async def fake_chat(system, messages, cfg):
            if cfg["base"] == "https://primary":
                raise RuntimeError("主端点故障")
            return "来自备用"

        async def run():
            return await chat_with_fallback(
                "s", [], {"base": "https://primary", "key": "k", "model": "m"},
                {"base": "https://backup", "key": "k2", "model": "m2"},
                chat_fn=fake_chat,
            )

        answer, used = asyncio.run(run())
        assert answer == "来自备用"
        assert used == "fallback"

    def test_no_fallback_raises(self):
        async def fake_chat(system, messages, cfg):
            raise RuntimeError("故障")

        async def run():
            await chat_with_fallback(
                "s", [], {"base": "https://primary", "key": "k", "model": "m"},
                None, chat_fn=fake_chat,
            )

        try:
            asyncio.run(run())
            raised = False
        except RuntimeError:
            raised = True
        assert raised

    def test_fallback_key_encrypted_in_settings(self, client, auth_headers):
        client.put("/api/settings/", json={
            "ai_mode": "byok", "ai_api_key": "sk-primary",
            "ai_fallback_url": "https://backup.example", "ai_fallback_key": "sk-backup-key-123",
            "ai_fallback_model": "backup-model",
        }, headers=auth_headers)
        settings = client.get("/api/settings/", headers=auth_headers).json()
        assert settings["ai_fallback_configured"] is True
        assert "sk-backup-key-123" not in str(settings)
