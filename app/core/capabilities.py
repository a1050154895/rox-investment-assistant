"""功能能力门控 — 单一事实源。

「收缩」不是删代码，而是诚实地声明哪些功能在缺少授权数据时会误导用户，
统一在此处控制开关；未来接入授权数据源后，只需把对应项改为 enabled 即可恢复。
"""
from __future__ import annotations

from typing import Any

CAPABILITIES: dict[str, dict[str, Any]] = {
    "backtest": {
        "status": "disabled",
        "reason": "回测需要授权历史行情才能保证结果可信；当前公共数据不满足回测精度，为避免误导已暂停。",
    },
    "screener": {
        "status": "disabled",
        "reason": "选股扫描需要授权实时行情；当前快照数据可能过期，排名会误导，已暂停。",
    },
    "alerts": {
        "status": "disabled",
        "reason": "价格预警需要稳定实时行情才能可靠触发；当前数据源不满足，已暂停。",
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
