"""AI 助手服务 — OpenAI 兼容 chat/completions 调用。

配置优先级：环境变量（AI_API_KEY / AI_API_BASE / AI_MODEL）> 用户设置（数据库）。
未配置时由 API 层返回明确错误，不降级为编造回复。
"""
import os
from typing import Any

import httpx

DEFAULT_BASE = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
TIMEOUT_SECONDS = 60.0


def resolve_ai_config(settings: dict[str, Any] | None = None) -> dict[str, str]:
    settings = settings or {}
    base = (os.getenv("AI_API_BASE", "").strip() or settings.get("ai_api_url") or DEFAULT_BASE).rstrip("/")
    key = os.getenv("AI_API_KEY", "").strip() or settings.get("ai_api_key") or ""
    model = os.getenv("AI_MODEL", "").strip() or settings.get("ai_model") or DEFAULT_MODEL
    return {"base": base, "key": key, "model": model}


def is_configured(cfg: dict[str, str]) -> bool:
    return bool(cfg.get("key"))


async def chat(system: str, messages: list[dict[str, str]], cfg: dict[str, str]) -> str:
    """调用 OpenAI 兼容接口。失败时抛出异常，由 API 层转为友好错误。"""
    url = f"{cfg['base']}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": 0.4,
        "max_tokens": 1200,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError):
            raise RuntimeError("AI 服务返回格式异常")


async def chat_stream(system: str, messages: list[dict[str, str]], cfg: dict[str, str]):
    """流式调用 OpenAI 兼容接口，逐 chunk yield delta 文本。"""
    url = f"{cfg['base']}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": 0.4,
        "max_tokens": 1200,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                if line == "data: [DONE]":
                    break
                try:
                    import json as _json
                    chunk = _json.loads(line[6:])
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except Exception:
                    continue
