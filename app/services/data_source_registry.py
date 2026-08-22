"""DataSourceRegistry：统一登记所有外部数据源及其真实健康状态。

服务层在每次抓取后调用 record()/record_result()，注册表记录
成功/失败时间与连续失败次数；健康面板和 /api/data/sources 直接消费。
不做主动拨测，健康状态全部来自真实请求，不伪造。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.services.data_contract import normalize_status


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SourceState:
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    last_latency_ms: int | None = None
    last_error: str | None = None


@dataclass
class DataSource:
    id: str
    name: str
    provider: str
    data_types: list[str]
    realtime: bool
    authorization: str
    degrade_to: str | None = None
    state: SourceState = field(default_factory=SourceState)


# data_source 字符串（服务层写进结果里的名字）→ 注册表 ID
_SOURCE_ALIASES = {
    "腾讯自选股公开接口": "tencent_quote",
    "腾讯实时行情": "tencent_quote",
    "新浪财经公开接口": "sina_quote",
    "AKShare/东方财富公开接口": "akshare_eastmoney",
    "东方财富公开接口": "akshare_eastmoney",
    "NeoData 历史快照": "neodata_snapshot",
    "历史快照": "neodata_snapshot",
    "公开资讯（AKShare 汇聚）": "akshare_news",
    "国家统计局/央行（AKShare）": "macro_official",
    "基金公开行情": "fund_market",
}

SOURCES: dict[str, DataSource] = {}


def _register(source: DataSource) -> None:
    SOURCES[source.id] = source


_register(DataSource("tencent_quote", "腾讯实时行情", "腾讯自选股公开接口",
                     ["个股行情", "指数行情", "ETF场内行情"], True, "公开接口，未商用授权", degrade_to="sina_quote"))
_register(DataSource("sina_quote", "新浪实时行情", "新浪财经公开接口",
                     ["个股行情"], True, "公开接口，未商用授权", degrade_to="akshare_eastmoney"))
_register(DataSource("akshare_eastmoney", "AKShare/东方财富", "AKShare · 东方财富公开接口",
                     ["个股行情", "K线", "资金流", "股票列表"], False, "开源库聚合，未商用授权",
                     degrade_to="neodata_snapshot"))
_register(DataSource("neodata_snapshot", "历史快照兜底", "NeoData 本地快照",
                     ["个股行情", "指数行情", "K线"], False, "自建快照，仅兜底展示"))
_register(DataSource("akshare_news", "公开资讯聚合", "AKShare 新闻/公告接口",
                     ["资讯线索", "行业资金流"], False, "公开信息聚合，注意新闻版权"))
_register(DataSource("macro_official", "官方宏观数据", "国家统计局 / 央行（经 AKShare）",
                     ["宏观指标"], False, "官方公开发布"))
_register(DataSource("fund_market", "基金公开行情", "腾讯/东财公开行情",
                     ["ETF场内行情", "ETF价格K线"], True, "公开接口，未商用授权"))

_lock = threading.Lock()


def record(source_id: str, ok: bool, latency_ms: int | None = None, error: str | None = None) -> None:
    """记录一次真实请求结果。"""
    with _lock:
        source = SOURCES.get(source_id)
        if not source:
            return
        now = _now()
        if ok:
            source.state.last_success_at = now
            source.state.consecutive_failures = 0
            source.state.last_latency_ms = latency_ms
        else:
            source.state.last_failure_at = now
            source.state.consecutive_failures += 1
            source.state.last_error = error


def record_result(result: dict[str, Any], latency_ms: int | None = None) -> None:
    """根据服务层返回结果里的 data_source/data_status 自动记账。

    realtime/snapshot/partial 视为成功；stale（快照过期兜底）与
    unavailable 视为失败——快照兜底说明上游已不可用。
    """
    source_id = _SOURCE_ALIASES.get(str(result.get("data_source") or ""))
    if not source_id:
        return
    status = normalize_status(result.get("data_status"))
    ok = status in ("realtime", "snapshot", "partial")
    record(source_id, ok, latency_ms=latency_ms, error=None if ok else str(result.get("message") or status))


def _health_of(source: DataSource) -> str:
    state = source.state
    if state.last_success_at is None and state.last_failure_at is None:
        return "unknown"
    if state.consecutive_failures == 0 and state.last_success_at:
        return "healthy"
    if state.consecutive_failures >= 3:
        return "down"
    return "degraded"


def health_report() -> dict[str, Any]:
    """全部数据源健康状态 + 汇总。"""
    sources = []
    summary = {"healthy": 0, "degraded": 0, "down": 0, "unknown": 0}
    for source in SOURCES.values():
        health = _health_of(source)
        summary[health] += 1
        sources.append({
            "id": source.id,
            "name": source.name,
            "provider": source.provider,
            "data_types": source.data_types,
            "realtime": source.realtime,
            "authorization": source.authorization,
            "degrade_to": source.degrade_to,
            "health": health,
            "last_success_at": source.state.last_success_at.isoformat() if source.state.last_success_at else None,
            "last_failure_at": source.state.last_failure_at.isoformat() if source.state.last_failure_at else None,
            "consecutive_failures": source.state.consecutive_failures,
            "last_latency_ms": source.state.last_latency_ms,
            "last_error": source.state.last_error,
        })
    return {
        "contract": {
            "statuses": ["realtime", "snapshot", "stale", "unavailable", "partial"],
            "fields": ["data_status", "data_source", "as_of", "stale", "coverage", "message"],
        },
        "summary": summary,
        "sources": sources,
        "updated_at": _now().isoformat(),
    }
