"""统一数据状态契约。

所有对外数据对象最终都应携带同一组字段：

    data_status: realtime | snapshot | stale | unavailable | partial
    data_source: 来源名称（可读）
    as_of:       数据时间
    stale:       是否过期（由状态推导或显式传入）
    coverage:    full | partial
    message:     降级/缺失说明

历史遗留写法（available/degraded/calculated 等）在出口处统一映射，
不要求一次改完所有服务，出口保证契约一致即可。
"""
from __future__ import annotations

from typing import Any

VALID_STATUSES = ("realtime", "snapshot", "stale", "unavailable", "partial")

STATUS_LABELS = {
    "realtime": "实时",
    "snapshot": "快照",
    "stale": "过期",
    "unavailable": "不可用",
    "partial": "部分可用",
}

# 历史状态 → 契约状态（宁可保守，不把快照冒充实时）
_LEGACY_STATUS_MAP = {
    "available": "snapshot",
    "ok": "realtime",
    "live": "realtime",
    "degraded": "partial",
    "calculated": "snapshot",
    "error": "unavailable",
    "failed": "unavailable",
    "": "unavailable",
}


def normalize_status(value: Any) -> str:
    """把任意历史写法映射成契约五态；未知值按不可用处理。"""
    status = str(value or "").strip().lower()
    if status in VALID_STATUSES:
        return status
    return _LEGACY_STATUS_MAP.get(status, "unavailable")


def status_block(
    status: Any,
    source: Any = None,
    as_of: Any = None,
    message: Any = None,
    coverage: str = "full",
    stale: bool | None = None,
) -> dict[str, Any]:
    """构造一个符合契约的状态块。"""
    normalized = normalize_status(status)
    if stale is None:
        stale = normalized in ("stale", "unavailable")
    return {
        "data_status": normalized,
        "status_label": STATUS_LABELS[normalized],
        "data_source": source or None,
        "as_of": as_of or None,
        "stale": bool(stale),
        "coverage": "partial" if normalized == "partial" else coverage,
        "message": message or None,
    }


_CONTRACT_KEYS = ("data_status", "data_source", "as_of", "stale", "coverage", "message")


def ensure_contract(payload: dict[str, Any], **defaults: Any) -> dict[str, Any]:
    """就地补齐/规范化一个数据对象的状态字段。

    保留原有字段，只覆盖契约相关键；未提供 data_status 的对象按
    unavailable 处理，避免"看起来有数据但其实没来源"。
    """
    if not isinstance(payload, dict):
        return payload
    block = status_block(
        defaults.get("status", payload.get("data_status", payload.get("status"))),
        defaults.get("data_source", payload.get("data_source")),
        defaults.get("as_of", payload.get("as_of")),
        defaults.get("message", payload.get("message")),
        coverage=defaults.get("coverage", payload.get("coverage", "full")),
        stale=defaults.get("stale", payload.get("stale")),
    )
    for key in _CONTRACT_KEYS:
        payload[key] = block[key]
    payload["status_label"] = block["status_label"]
    return payload
