"""功能能力门控 — 单一事实源。

「收缩」不是删代码，而是诚实地声明哪些功能在缺少授权数据时会误导用户，
统一在此处控制开关；未来接入授权数据源后，只需把对应项改为 enabled 即可恢复。
"""
from __future__ import annotations

from typing import Any

CAPABILITIES: dict[str, dict[str, Any]] = {
    # 腾讯实时行情/前复权K线接入后重新启用；结果均携带数据状态与来源标注。
    "backtest": {
        "status": "enabled",
        "note": "K线为腾讯前复权公开数据，费用模型含佣金/印花税/滑点；结果仅用于框架验证。",
    },
    "screener": {
        "status": "enabled",
        "note": "行情为腾讯实时接口；股票池为内置 ~80 只热门标的，非全市场，结果须结合个股透视复核。",
    },
    "alerts": {
        "status": "enabled",
        "note": "触发检测基于腾讯实时行情快照，刷新页面时检查；非推送式监控。",
    },
}


def is_enabled(key: str) -> bool:
    return CAPABILITIES.get(key, {}).get("status") == "enabled"


def disabled_response(key: str) -> dict[str, Any]:
    capability = CAPABILITIES.get(key, {})
    return {
        "status": "disabled",
        "reason": capability.get("reason", "该功能暂不可用。"),
    }


def disabled_if(key: str) -> dict[str, Any] | None:
    """功能未启用时返回 disabled 响应体；启用时返回 None。"""
    return disabled_response(key) if not is_enabled(key) else None
