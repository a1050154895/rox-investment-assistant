"""AI 助手 API — 三层模式状态 + 对话（真实调用 OpenAI 兼容接口）+ SSE 流式。

模式说明：
- off      不使用 AI：AI 端点返回 AI_DISABLED，核心功能不受影响。
- platform 平台 AI：使用服务端环境变量配置。
- byok     自带模型：使用用户自己的 Base URL / Key / 模型（Key 加密落库）。
所有 AI 输出都是「模型辅助」，不是事实来源，不能覆盖硬性风控。
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.crypto import decrypt_secret
from app.db import get_db
from app.models import Setting, User
from app.services.ai_service import (
    chat_stream, chat_with_fallback, is_configured,
    resolve_ai_config, resolve_fallback_config,
)

router = APIRouter()

SYSTEM_PROMPT = (
    "你是 ROX 投资助手的「研究助手」。ROX 的定位是投资认知系统：帮助用户记录决策、追踪矛盾、"
    "执行 334 仓位纪律（核心30%/卫星30%/现金40%，仓位由可承受风险反推）。"
    "你的职责：只解释风险与纪律冲突、追问证据、帮助复盘认知过程。"
    "铁律：不预测涨跌、不推荐个股买卖、不覆盖用户的硬性风控规则、不编造数据或消息。"
    "回答须简洁（300字内）、结构化，结尾提示'以上为模型辅助，不构成投资建议'。"
)

AI_DISABLED = {
    "code": "AI_DISABLED",
    "message": "当前为「不使用 AI」模式，核心投研功能不受影响；如需 AI 辅助，请在设置中切换为平台 AI 或自带模型。",
}
AI_UNCONFIGURED = {
    "code": "AI_NOT_CONFIGURED",
    "message": "AI 服务未配置。平台 AI 需要服务端配置，或在设置中切换到「使用我的模型」并填写 API Key。",
}


def _load_user_settings(db: Session, user_id: int) -> dict:
    """读取用户设置；BYOK 密钥解密后仅在本请求内使用。"""
    rows = db.query(Setting).filter(Setting.user_id == user_id).all()
    settings = {r.key: r.value for r in rows}
    for key_field in ("ai_api_key", "ai_fallback_key"):
        if settings.get(key_field):
            settings[key_field] = decrypt_secret(settings[key_field])
    return settings


def _resolve_or_raise(db: Session, user_id: int) -> dict:
    settings = _load_user_settings(db, user_id)
    cfg = resolve_ai_config(settings)
    if cfg.get("mode") == "off":
        raise HTTPException(status_code=503, detail=AI_DISABLED)
    if not is_configured(cfg):
        raise HTTPException(status_code=503, detail=AI_UNCONFIGURED)
    return cfg


@router.get("/status")
async def ai_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 三层模式与配置状态（不回传密钥）。"""
    settings = _load_user_settings(db, user.id)
    cfg = resolve_ai_config(settings)
    mode = cfg.get("mode", "platform")
    return {
        "mode": mode,
        "configured": mode != "off" and is_configured(cfg),
        "provider": (cfg["base"].split("//")[-1].split(".")[0] if cfg["base"] else ""),
        "model": cfg["model"],
        "source": "env" if mode == "platform" else ("user_settings" if mode == "byok" else "off"),
        "platform_ai_available": bool(os.getenv("AI_API_KEY", "").strip()),
        "note": "AI 输出为模型辅助，不是事实来源，不覆盖硬性风控。",
    }


class ChatIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    context: str | None = Field(None, max_length=4000, description="可选上下文（如纪律评估结果）")


# AI 研究流程应用：只做整理/追问/拆分，不做结论。输出必须回链用户自己的内容。
RESEARCH_ASSIST_ACTIONS = {
    "question": (
        "把下面的研究问题改写成一个【可验证、可证伪】的研究问题："
        "明确验证对象、时间范围、判断标准和失效条件。输出改写后的问题和一句理由，不要给出多空结论。"
    ),
    "counter": (
        "针对下面的研究判断，从三个视角各列 1-2 条【应该主动寻找的反证角度】："
        "①趋势视角（如果趋势交易者看空，他会指出什么？量价/动量/关键位）；"
        "②价值视角（如果价值投资者反对，他会质疑什么？护城河/现金流/估值锚）；"
        "③风控视角（纪律与风险控制会拒绝什么？仓位/止损/相关性/拥挤度）。"
        "每条注明可用什么公开数据/事件来检验。只提供检验角度，不要下结论，"
        "不要扮演任何具体人物。"
    ),
    "classify": (
        "把下面的文本拆分为三类：【事实】（有来源可核验）、【观点/推断】（作者判断）、"
        "【待验证】（需要查证）。逐条标注，不确定的归入待验证，不要编造来源。"
    ),
}


class ResearchAssistIn(BaseModel):
    action: str = Field(..., description="question=改写研究问题, counter=反证提示, classify=事实观点拆分")
    content: str = Field(..., min_length=1, max_length=2000)
    title: str | None = Field(None, max_length=120)


@router.post("/research-assist")
async def research_assist(
    body: ResearchAssistIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 研究流程辅助：改写问题 / 反证提示 / 事实-观点拆分。

    遵守三层模式与 BYOK failover；输出仅为建议，不自动写入研究卡，
    也不代表事实——用户需自行核验并回链原始证据。
    """
    instruction = RESEARCH_ASSIST_ACTIONS.get(body.action)
    if not instruction:
        raise HTTPException(status_code=422, detail=f"action 必须是 {sorted(RESEARCH_ASSIST_ACTIONS)} 之一")
    cfg = _resolve_or_raise(db, user.id)

    user_content = f"[研究对象]\n{body.title or '未提供'}\n\n[内容]\n{body.content}"
    fallback = resolve_fallback_config(_load_user_settings(db, user.id))
    try:
        answer, provider_used = await chat_with_fallback(
            f"{SYSTEM_PROMPT}\n本次任务：{instruction}",
            [{"role": "user", "content": user_content}],
            cfg, fallback,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail={"code": "AI_CALL_FAILED", "message": "AI 研究辅助调用失败，请检查配置或稍后重试。"},
        ) from exc
    return {
        "action": body.action,
        "output": answer,
        "provider_used": provider_used,
        "ai_note": "模型辅助建议，不是事实来源；采纳前请自行核验并回链原始证据。",
    }


@router.post("/chat")
async def chat_endpoint(
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 对话 — 真实调用后端模型。未配置或调用失败时返回明确错误。"""
    cfg = _resolve_or_raise(db, user.id)

    user_content = body.question
    if body.context:
        user_content = f"[上下文]\n{body.context}\n\n[问题]\n{body.question}"

    fallback = resolve_fallback_config(_load_user_settings(db, user.id))
    try:
        answer, provider_used = await chat_with_fallback(
            SYSTEM_PROMPT, [{"role": "user", "content": user_content}], cfg, fallback,
        )
    except Exception as exc:  # noqa: BLE001 — 统一转为友好错误
        raise HTTPException(
            status_code=502,
            detail={"code": "AI_CALL_FAILED", "message": "AI 服务调用失败，请检查 API 地址、Key 与模型名称是否正确，或稍后重试。"},
        ) from exc
    return {
        "answer": answer,
        "provider_used": provider_used,
        "fallback_enabled": bool(fallback),
        "ai_note": "模型辅助，不是事实来源",
    }


@router.post("/chat/stream")
async def chat_stream_endpoint(
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 流式对话 — SSE 逐 token 推送。"""
    cfg = _resolve_or_raise(db, user.id)

    user_content = body.question
    if body.context:
        user_content = f"[上下文]\n{body.context}\n\n[问题]\n{body.question}"

    async def _stream():
        try:
            async for token in chat_stream(SYSTEM_PROMPT, [{"role": "user", "content": user_content}], cfg):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            yield 'data: {"error":"AI流式调用失败"}\n\n'

    return StreamingResponse(_stream(), media_type="text/event-stream")
