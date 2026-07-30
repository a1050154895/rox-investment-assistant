"""334 仓位纪律确定性评估引擎。"""
from __future__ import annotations

from typing import Any


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def evaluate_discipline(profile: dict[str, Any]) -> dict[str, Any]:
    """根据用户风险预算反推仓位边界，不提供方向性交易结论。"""
    core = _clamp(profile.get("core_pct", 0))
    satellite = _clamp(profile.get("satellite_pct", 0))
    cash = _clamp(profile.get("cash_pct", 0))
    allocation_total = round(core + satellite + cash, 2)

    max_total_position = _clamp(profile.get("max_total_position_pct", 60))
    risk_budget = _clamp(profile.get("single_trade_risk_pct", 1), 0.1, 20)
    stop_loss = _clamp(profile.get("stop_loss_pct", 8), 0.1, 100)
    single_position_limit = _clamp(profile.get("single_position_limit_pct", 15), 0.1, 100)
    sector_limit = _clamp(profile.get("sector_limit_pct", 30), 0.1, 100)
    current_sector = _clamp(profile.get("current_sector_exposure_pct", 0))
    planned_position = _clamp(profile.get("planned_position_pct", 0))
    monthly_trades = max(0, int(profile.get("monthly_trades", 0)))
    monthly_trade_limit = max(1, int(profile.get("monthly_trade_limit", 2)))

    invested = round(core + satellite, 2)
    risk_position_limit = round(_clamp(risk_budget / stop_loss * 100), 2)
    allowed_position = round(min(risk_position_limit, single_position_limit), 2)

    checks: list[dict[str, Any]] = []

    def add_check(key: str, passed: bool, title: str, detail: str) -> None:
        checks.append({"key": key, "passed": passed, "title": title, "detail": detail})

    add_check(
        "allocation",
        abs(allocation_total - 100) <= 0.01,
        "仓位合计",
        f"核心、卫星和现金合计 {allocation_total:.1f}%，应等于 100%。",
    )
    add_check(
        "total_position",
        invested <= max_total_position,
        "总仓位上限",
        f"当前权益仓位 {invested:.1f}%，上限 {max_total_position:.1f}%。",
    )
    add_check(
        "single_position",
        planned_position <= allowed_position,
        "计划单票仓位",
        f"按风险预算反推上限 {allowed_position:.1f}%（风险预算 {risk_budget:.1f}% ÷ 止损距离 {stop_loss:.1f}%），计划 {planned_position:.1f}%。",
    )
    add_check(
        "sector_concentration",
        current_sector <= sector_limit,
        "行业集中度",
        f"当前行业暴露 {current_sector:.1f}%，上限 {sector_limit:.1f}%。",
    )
    add_check(
        "turnover",
        monthly_trades <= monthly_trade_limit,
        "操作频率",
        f"本月已操作 {monthly_trades} 次，纪律上限 {monthly_trade_limit} 次。",
    )

    violations = [item for item in checks if not item["passed"]]
    if violations:
        status = "blocked"
        status_label = "存在纪律冲突"
        guidance = "先修正未通过项，再讨论加仓或新开仓；硬纪律不应被主观信心覆盖。"
    elif planned_position == 0:
        status = "ready"
        status_label = "风险边界已建立"
        guidance = "风险参数已通过检查。填写计划仓位后，可进一步验证单票风险是否可承受。"
    else:
        status = "within_limits"
        status_label = "计划处于边界内"
        guidance = "当前只代表仓位风险可承受，不代表标的方向正确；仍需验证基本面、价格与退出条件。"

    coach_questions = [
        "如果开盘直接跳空跌破止损位，实际损失是否仍在风险预算内？",
        "这笔交易与现有持仓是否属于同一行业或同一风险因子？",
        "加仓依据是原逻辑被新证据强化，还是仅因为价格上涨或下跌？",
    ]
    if current_sector > sector_limit:
        coach_questions.insert(0, "当前行业暴露已超上限，新仓是否会继续放大同一风险？")
    if monthly_trades > monthly_trade_limit:
        coach_questions.insert(0, "操作频率已超纪律上限，这次操作是否真的来自新证据？")

    return {
        "status": status,
        "status_label": status_label,
        "guidance": guidance,
        "allocation": {"core": core, "satellite": satellite, "cash": cash, "total": allocation_total},
        "limits": {
            "invested_pct": invested,
            "risk_position_limit_pct": risk_position_limit,
            "allowed_position_pct": allowed_position,
            "max_total_position_pct": max_total_position,
        },
        "checks": checks,
        "coach_questions": coach_questions,
        "method": "单笔风险预算 ÷ 止损距离 = 风险仓位上限；再与单票上限取较小值。",
        "disclaimer": "纪律评估只检查风险边界，不构成投资建议或买卖信号。",
    }
