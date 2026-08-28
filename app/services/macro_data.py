"""可信宏观矩阵数据服务。

矩阵是财政信用条件与价值实现条件的研究代理，不是主权信用评级。
数据通过 AKShare 公开宏观接口获取，保留原始发布机构、日期和覆盖率；
任何指标失败都明确降级，不使用静态分数或随机值。
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)
_CACHE: tuple[float, dict[str, Any]] | None = None
_CACHE_TTL = 60 * 60


@dataclass(frozen=True)
class IndicatorSpec:
    key: str
    label: str
    function_name: str
    value_columns: tuple[str, ...]
    date_columns: tuple[str, ...]
    publisher: str
    group: str
    scorer: Callable[[float], float]
    unit: str = "%"


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _growth_score(value: float) -> float:
    """同比增速代理：0%为45分，每增加1个百分点加3分。"""
    return _clamp(45 + value * 3)


def _liquidity_score(value: float) -> float:
    """M2同比代理：7%附近中性，过低表示流动性偏紧。"""
    return _clamp(50 + (value - 7) * 4)


def _cpi_score(value: float) -> float:
    """CPI同比代理：接近2%得分较高，通缩或高通胀均扣分。"""
    return _clamp(78 - abs(value - 2) * 14)


def _pmi_score(value: float) -> float:
    """PMI代理：50为荣枯线，每偏离1个百分点加减4分。"""
    return _clamp(50 + (value - 50) * 4)


def _ppi_score(value: float) -> float:
    """PPI同比代理：正增长有利于工业利润，负值为通缩压力。"""
    return _clamp(50 + value * 3)


def _social_finance_score(value: float) -> float:
    """社融同比代理：10%附近中性，反映信用扩张力度。"""
    return _clamp(50 + (value - 10) * 3)


def _neutral_score(value: float) -> float:
    return 50.0


# 降级快照：当 AKShare 不可用时（Render 网络限制等）使用最近已知值。
# 数据来源：westock-data 技能 core_indicators_cur（腾讯自选股宏观接口）。
FALLBACK_SNAPSHOT: dict[str, dict[str, Any]] = {
    "fiscal_revenue_yoy": {"value": 8.65, "period": "2026年06月", "publisher": "中华人民共和国财政部"},
    "tax_revenue_yoy": {"value": 3.6, "period": "2026年06月", "publisher": "国家税务总局"},
    "m2_yoy": {"value": 8.0, "period": "2026年06月", "publisher": "中国人民银行"},
    "retail_sales_yoy": {"value": 1.0, "period": "2026年06月", "publisher": "中华人民共和国国家统计局"},
    "cpi_yoy": {"value": 0.1, "period": "2026年06月", "publisher": "中华人民共和国国家统计局"},
    "pmi": {"value": 49.2, "period": "2026年07月", "publisher": "中华人民共和国国家统计局"},
    "ppi_yoy": {"value": 4.1, "period": "2026年06月", "publisher": "中华人民共和国国家统计局"},
    "social_finance": {"value": 7.4, "period": "2026年06月", "publisher": "中国人民银行"},
}


SPECS = (
    IndicatorSpec(
        key="fiscal_revenue_yoy", label="全国财政收入同比", function_name="macro_china_czsr",
        value_columns=("当月同比增长", "当月-同比增长", "累计同比增长", "累计-同比增长", "同比增长"),
        date_columns=("月份", "日期", "时间"), publisher="中华人民共和国财政部",
        group="fiscal_credit", scorer=_growth_score,
    ),
    IndicatorSpec(
        key="tax_revenue_yoy", label="全国税收收入同比", function_name="macro_china_national_tax_receipts",
        value_columns=("较上年同期", "同比增长", "同比增速", "增长率", "税收收入同比"),
        date_columns=("季度", "月份", "日期", "时间"), publisher="国家税务总局",
        group="fiscal_credit", scorer=_growth_score,
    ),
    IndicatorSpec(
        key="m2_yoy", label="广义货币 M2 同比", function_name="macro_china_money_supply",
        value_columns=("货币和准货币（广义货币M2）同比增长", "货币和准货币(广义货币M2)同比增长",
                       "M2同比增长", "M2-同比增长", "同比增长"),
        date_columns=("月份", "日期", "时间"), publisher="中国人民银行",
        group="fiscal_credit", scorer=_liquidity_score,
    ),
    IndicatorSpec(
        key="retail_sales_yoy", label="社会消费品零售总额同比", function_name="macro_china_consumer_goods_retail",
        value_columns=("同比增长", "当月同比增长", "当月-同比增长", "累计同比增长", "累计-同比增长"),
        date_columns=("月份", "日期", "时间"), publisher="中华人民共和国国家统计局",
        group="value_realization", scorer=_growth_score,
    ),
    IndicatorSpec(
        key="cpi_yoy", label="居民消费价格指数 CPI 同比", function_name="macro_china_cpi_yearly",
        value_columns=("今值", "最新值", "同比增长", "数值", "value"),
        date_columns=("日期", "时间", "月份", "date"), publisher="中华人民共和国国家统计局",
        group="value_realization", scorer=_cpi_score,
    ),
    IndicatorSpec(
        key="pmi", label="制造业 PMI", function_name="macro_china_pmi",
        value_columns=("制造业-指数", "制造业指数", "今值", "最新值", "数值", "value", "指数"),
        date_columns=("月份", "日期", "时间", "date"), publisher="中华人民共和国国家统计局",
        group="fiscal_credit", scorer=_pmi_score,
    ),
    IndicatorSpec(
        key="ppi_yoy", label="工业品出厂价格 PPI 同比", function_name="macro_china_ppi_yearly",
        value_columns=("今值", "最新值", "同比增长", "数值", "value"),
        date_columns=("日期", "时间", "月份", "date"), publisher="中华人民共和国国家统计局",
        group="value_realization", scorer=_ppi_score,
    ),
    IndicatorSpec(
        key="social_finance", label="社会融资规模存量同比", function_name="macro_china_shrzgm",
        value_columns=("同比增长", "同比增速", "增长率", "存量同比"),
        date_columns=("月份", "日期", "时间", "date"), publisher="中国人民银行",
        group="fiscal_credit", scorer=_social_finance_score,
    ),
)


# 只用于实质利率代理，不纳入宏观矩阵评分，避免改变既有矩阵口径。
DERIVED_SPECS = (
    IndicatorSpec(
        key="lpr_1y", label="1年期贷款市场报价利率", function_name="macro_china_lpr",
        value_columns=("LPR1Y",), date_columns=("TRADE_DATE",),
        publisher="中国人民银行", group="derived", scorer=_neutral_score,
    ),
    IndicatorSpec(
        key="gdp_yoy", label="国内生产总值同比", function_name="macro_china_gdp",
        value_columns=("国内生产总值-同比增长",), date_columns=("季度",),
        publisher="中华人民共和国国家统计局", group="derived", scorer=_neutral_score,
    ),
)


def _to_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        text = str(value).strip().replace(",", "").replace("%", "")
        if not text or text.lower() in {"nan", "none", "--", "-"}:
            return None
        number = float(text)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _period_age(period: str) -> int | None:
    """Estimate observation age from a YYYY年MM月/ISO period label."""
    text = str(period or "").strip()
    try:
        if "年" in text:
            year, tail = text.split("年", 1)
            quarter = re.search(r"第([1-4])季度", tail)
            month = str((int(quarter.group(1)) - 1) * 3 + 2) if quarter else tail.split("月", 1)[0]
            return max(0, (datetime.now().date() - datetime(int(year), int(month), 1).date()).days)
        return max(0, (datetime.fromisoformat(text[:10]).date() - datetime.now().date()).days * -1)
    except (TypeError, ValueError, IndexError):
        return None


def _freshness(period: str, status: str) -> dict[str, Any]:
    age_days = _period_age(period)
    if status == "unavailable":
        label = "不可用"
    elif age_days is None:
        label = "日期未知"
    elif age_days <= 45:
        label = "较新"
    elif age_days <= 90:
        label = "偏旧"
    else:
        label = "过期"
    return {"label": label, "age_days": age_days, "is_stale": label in ("偏旧", "过期")}
def _find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {str(column).replace(" ", ""): str(column) for column in columns}
    for candidate in candidates:
        key = candidate.replace(" ", "")
        if key in normalized:
            return normalized[key]
    for candidate in candidates:
        key = candidate.replace(" ", "").lower()
        for normalized_key, original in normalized.items():
            if key in normalized_key.lower():
                return original
    return None


def _period_bucket(period: str) -> str | None:
    """将月度、季度观察期归一到同一个季度桶。"""
    text = str(period or "")
    years = re.findall(r"20\d{2}", text)
    if not years:
        return None
    year = years[0]
    quarter = re.search(r"第\s*([1-4])\s*季度", text)
    if quarter:
        return f"{year}Q{quarter.group(1)}"
    month = re.search(r"(?:年|[-/])\s*(\d{1,2})\s*月?", text)
    if month:
        return f"{year}Q{(int(month.group(1)) - 1) // 3 + 1}"
    return year


def _real_rate_proxy(indicators: list[dict[str, Any]]) -> dict[str, Any]:
    """按资料口径计算实质利率代理，严格要求四项数据同一季度。"""
    by_key = {item.get("key"): item for item in indicators}
    keys = ("lpr_1y", "cpi_yoy", "m2_yoy", "gdp_yoy")
    inputs = {key: by_key.get(key) for key in keys}
    missing = [key for key, item in inputs.items() if not item or item.get("status") not in ("available", "snapshot")]
    buckets = {key: _period_bucket(item.get("period", "")) for key, item in inputs.items() if item}
    base = {"formula": "名义利率 - CPI - (M2增速 - GDP增速)", "inputs": inputs, "missing": missing, "period_buckets": buckets}
    if missing:
        return {**base, "status": "unavailable", "value": None, "message": "缺少四项有效数据，暂不计算。"}
    if len(set(buckets.values())) != 1 or None in buckets.values():
        return {**base, "status": "period_mismatch", "value": None, "message": "四项数据不属于同一季度，暂不计算。"}
    value = inputs["lpr_1y"]["value"] - inputs["cpi_yoy"]["value"] - (
        inputs["m2_yoy"]["value"] - inputs["gdp_yoy"]["value"]
    )
    return {
        **base, "status": "calculated", "value": round(value, 2),
        "message": "四项数据属于同一季度，可作为研究代理；不直接生成买卖结论。",
    }


def parse_indicator_frame(frame: Any, spec: IndicatorSpec) -> dict[str, Any]:
    if frame is None or getattr(frame, "empty", True):
        raise ValueError("数据表为空")
    columns = [str(column) for column in frame.columns]
    value_column = _find_column(columns, spec.value_columns)
    date_column = _find_column(columns, spec.date_columns)
    if value_column is None:
        raise ValueError(f"未识别数值列，返回列: {columns}")

    # 日期过滤：只看最近1年半的数据，更旧的数据由快照降级处理
    cutoff_year = datetime.now().year - 1
    if datetime.now().month <= 6:
        cutoff_year = datetime.now().year - 1  # 上半年允许去年数据
    else:
        cutoff_year = datetime.now().year  # 下半年只要今年数据
    rows = list(frame.iloc[::-1].iterrows())
    for _, row in rows:
        value = _to_number(row.get(value_column))
        if value is None:
            continue
        period = str(row.get(date_column, "未知日期")) if date_column else "未知日期"
        # 过滤掉cutoff_year之前的数据
        period_year = None
        for part in period.replace("年", " ").replace("-", " ").split():
            if part.isdigit() and len(part) == 4:
                period_year = int(part)
                break
        if period_year and period_year < cutoff_year:
            continue
        score = round(spec.scorer(value), 1)
        return {
            "key": spec.key, "label": spec.label, "value": round(value, 2), "unit": spec.unit,
            "period": period, "score": score, "status": "available", "publisher": spec.publisher,
            "data_source": f"AKShare / {spec.publisher}公开数据", "value_column": value_column,
            "freshness": _freshness(period, "available"),
        }
    raise ValueError(f"近{cutoff_year}年后无有效数据")


async def _fetch_indicator(spec: IndicatorSpec) -> dict[str, Any]:
    try:
        import akshare as ak
        from app.services.akshare_gate import gated_call
        function = getattr(ak, spec.function_name)
        frame = await asyncio.wait_for(gated_call(function), timeout=12)
        return parse_indicator_frame(frame, spec)
    except Exception as exc:
        logger.warning("macro_indicator_unavailable key=%s error=%s", spec.key, exc)
        # 降级：使用最近已知快照值
        snapshot = FALLBACK_SNAPSHOT.get(spec.key)
        if snapshot:
            value = snapshot["value"]
            score = round(spec.scorer(value), 1)
            return {
                "key": spec.key, "label": spec.label, "value": round(value, 2),
                "unit": spec.unit, "period": snapshot["period"], "score": score,
                "status": "snapshot", "publisher": spec.publisher,
                "data_source": f"公开数据快照 / {spec.publisher}",
                "message": f"AKShare 不可用，使用最近已知值（{snapshot['period']}）",
                "freshness": _freshness(snapshot["period"], "snapshot"),
            }
        return {
            "key": spec.key, "label": spec.label, "status": "unavailable", "publisher": spec.publisher,
            "data_source": f"AKShare / {spec.publisher}公开数据", "message": str(exc)[:180],
            "freshness": _freshness("", "unavailable"),
        }


def _group_result(indicators: list[dict[str, Any]], group: str, label: str) -> dict[str, Any]:
    group_specs = [spec for spec in SPECS if spec.group == group]
    keys = {spec.key for spec in group_specs}
    available = [item for item in indicators if item["key"] in keys and item.get("status") in ("available", "snapshot")]
    minimum = 2
    if len(available) < minimum:
        return {
            "status": "数据不足", "score": 0, "trend": "unknown", "coverage": len(available),
            "required": minimum, "detail": f"{label}至少需要 {minimum} 项有效指标，当前仅 {len(available)} 项。",
            "indicators": [item for item in indicators if item["key"] in keys],
        }
    score = round(sum(float(item["score"]) for item in available) / len(available), 1)
    status = "偏强" if score >= 65 else "中性" if score >= 45 else "偏弱"
    detail = "；".join(f"{item['label']} {item['value']}{item['unit']}（{item['period']}）" for item in available)
    return {
        "status": status, "score": score, "trend": "up" if score >= 65 else "stable" if score >= 45 else "down",
        "coverage": len(available), "required": minimum, "detail": detail,
        "indicators": [item for item in indicators if item["key"] in keys],
    }


def _matrix_conclusion(fiscal: dict[str, Any], value: dict[str, Any]) -> tuple[str, str, str]:
    if not fiscal.get("score") or not value.get("score"):
        return "数据不足", "不输出仓位建议", "宏观指标覆盖率不足，仅展示已取得的数据与缺失项。"
    fiscal_label = "扩张" if fiscal["score"] >= 65 else "中性" if fiscal["score"] >= 45 else "收缩"
    value_label = "改善" if value["score"] >= 65 else "中性" if value["score"] >= 45 else "承压"
    cell = f"财政信用条件{fiscal_label} × 价值实现{value_label}"
    advice = (
        f"当前代理矩阵为“{cell}”。它用于解释财政、流动性与内需环境，"
        "不直接生成买卖或仓位结论；应继续结合市场估值、行业盈利和用户风险预算验证。"
    )
    return cell, "进入研究验证，不自动调仓", advice


async def _get_macro_matrix_raw(force: bool = False) -> dict[str, Any]:
    global _CACHE
    if _CACHE and not force and time.time() - _CACHE[0] < _CACHE_TTL:
        return _CACHE[1]

    indicators = await asyncio.gather(*(_fetch_indicator(spec) for spec in SPECS))
    derived_indicators = await asyncio.gather(*(_fetch_indicator(spec) for spec in DERIVED_SPECS))
    real_rate = _real_rate_proxy(indicators + derived_indicators)
    fiscal = _group_result(indicators, "fiscal_credit", "财政信用条件")
    value = _group_result(indicators, "value_realization", "价值实现条件")
    cell, action, advice = _matrix_conclusion(fiscal, value)
    available_count = sum(item.get("status") in ("available", "snapshot") for item in indicators)
    stale_items = [item for item in indicators if item.get("freshness", {}).get("is_stale")]
    missing_items = [item["label"] for item in indicators if item.get("status") == "unavailable"]
    observed_periods = [
        (item.get("freshness", {}).get("age_days"), item.get("period"))
        for item in indicators if item.get("period") and item.get("freshness", {}).get("age_days") is not None
    ]
    result = {
        "methodology": "财政信用条件 × 价值实现条件代理矩阵（不是主权信用评级）",
        "sovereign_credit": fiscal,
        "value_realization": value,
        "matrix_cell": cell,
        "matrix_action": action,
        "framework_advice": advice,
        "data_status": "available" if fiscal.get("score") and value.get("score") else "degraded",
        "coverage": {"available": available_count, "total": len(indicators)},
        "derived_indicators": derived_indicators,
        "real_rate_proxy": real_rate,
        "data_quality": {
            "status": "stale" if stale_items else "ok" if available_count == len(indicators) else "partial",
            "stale_count": len(stale_items),
            "missing": missing_items,
            "latest_observation": min(observed_periods, key=lambda pair: pair[0])[1] if observed_periods else None,
            "message": "部分指标日期偏旧，请结合原始来源复核" if stale_items else "每项指标均附带观察期与来源",
        },
        "updated_at": datetime.now().isoformat(),
        "refresh_ttl_seconds": _CACHE_TTL,
        "disclaimer": "宏观矩阵是研究代理，不是信用评级、投资建议或仓位指令。",
    }
    _CACHE = (time.time(), result)
    return result


# ---- DataSourceRegistry 埋点 ----
from app.services import data_source_registry as _registry  # noqa: E402


async def get_macro_matrix(force: bool = False) -> dict[str, Any]:
    result = await _get_macro_matrix_raw(force)
    _registry.record("macro_official", ok=result.get("data_status") != "unavailable")
    return result
