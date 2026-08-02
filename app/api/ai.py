"""AI 助手 API — 状态查询 + 对话（真实调用 OpenAI 兼容接口）。"""
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import Setting, User
from app.services.ai_service import chat, is_configured, resolve_ai_config

router = APIRouter()

SYSTEM_PROMPT = (
    "你是 ROX 投资助手的「研究助手」。ROX 的定位是投资认知系统：帮助用户记录决策、追踪矛盾、"
    "执行 334 仓位纪律（核心30%/卫星30%/现金40%，仓位由可承受风险反推）。"
    "你的职责：只解释风险与纪律冲突、追问证据、帮助复盘认知过程。"
    "铁律：不预测涨跌、不推荐个股买卖、不覆盖用户的硬性风控规则、不编造数据或消息。"
    "回答须简洁（300字内）、结构化，结尾如有必要提示‘以上为认知辅助，不构成投资建议’。"
)

AI_UNCONFIGURED = {
    "code": "AI_NOT_CONFIGURED",
    "message": "AI 服务未配置。请在「设置 → AI模型」中填写 API Key，或联系管理员配置环境变量 AI_API_KEY。",
}


def _load_user_settings(db: Session, user_id: int) -> dict:
    """读取用户设置（含服务端内部的明文 AI Key）。"""
    rows = db.query(Setting).filter(Setting.user_id == user_id).all()
    return {r.key: r.value for r in rows}


@router.get("/status")
async def ai_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 服务配置状态（不回传密钥）。"""
    cfg = resolve_ai_config(_load_user_settings(db, user.id))
    return {
        "configured": is_configured(cfg),
        "provider": (cfg["base"].split("//")[-1].split(".")[0] if cfg["base"] else ""),
        "model": cfg["model"],
        "source": "env" if os.getenv("AI_API_KEY", "").strip() else "user_settings",
    }


class ChatIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    context: str | None = Field(None, max_length=4000, description="可选上下文（如纪律评估结果）")


@router.post("/chat")
async def chat_endpoint(
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 对话 — 真实调用后端模型。未配置或调用失败时返回明确错误。"""
    cfg = resolve_ai_config(_load_user_settings(db, user.id))
    if not is_configured(cfg):
        raise HTTPException(status_code=503, detail=AI_UNCONFIGURED)

    user_content = body.question
    if body.context:
        user_content = f"[上下文]\n{body.context}\n\n[问题]\n{body.question}"

    try:
        answer = await chat(SYSTEM_PROMPT, [{"role": "user", "content": user_content}], cfg)
    except Exception as exc:  # noqa: BLE001 — 统一转为友好错误
        raise HTTPException(
            status_code=502,
            detail={"code": "AI_CALL_FAILED", "message": "AI 服务调用失败，请检查 API 地址、Key 与模型名称是否正确，或稍后重试。"},
        ) from exc
    return {"answer": answer}
