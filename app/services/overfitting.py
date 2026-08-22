"""过拟合检查器（吸收自 ROX3.0 overfitting_detector 思想，轻量重写）。

两个诚实视角，只给风险提示，不给有效性证明：
- 参数敏感性：每个数值参数 ±20%（截断在策略声明范围内）重跑，
  若收益悬崖式衰减，说明结果依赖精调参数；
- 样本内外对比：前 70% 为样本内、后 30% 为样本外（信号在全序列上
  生成后分段评估，避免前视），样本外大幅衰减提示过拟合。
"""
from __future__ import annotations

from typing import Any

from app.services.backtest_engine import STRATEGIES, generate_signals, run_backtest

OOS_SPLIT = 0.7


def _spec_of(strategy_id: str) -> dict | None:
    return next((s for s in STRATEGIES if s["id"] == strategy_id), None)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _param_variants(strategy_id: str, params: dict) -> list[tuple[str, float, float]]:
    """(参数名, 基准值, 变体值)；整型参数保持整型，范围截断到策略声明。"""
    spec = _spec_of(strategy_id)
    if not spec:
        return []
    variants: list[tuple[str, float, float]] = []
    for p in spec.get("params", []):
        base = float(params.get(p["key"], p["default"]))
        lo, hi = float(p["min"]), float(p["max"])
        is_int = float(base).is_integer()
        for factor in (0.8, 1.2):
            v = base * factor
            v = float(int(round(v))) if is_int else round(v, 2)
            v = _clamp(v, lo, hi)
            if v != base and abs(v - base) >= (1 if is_int else 0.01):
                variants.append((p["key"], base, v))
    return variants


def _safe_run(candles: list[dict], strategy_id: str, params: dict, run_kwargs: dict) -> dict:
    try:
        return run_backtest(candles, generate_signals(strategy_id, candles, params), **run_kwargs)
    except Exception:  # noqa: BLE001 — 单次变体失败不拖垮整份报告
        return {}


def sensitivity_check(
    candles: list[dict], strategy_id: str, params: dict, run_kwargs: dict
) -> dict[str, Any]:
    base = _safe_run(candles, strategy_id, params, run_kwargs)
    base_ret = base.get("total_return", 0.0) or 0.0
    rows = []
    for key, base_val, variant_val in _param_variants(strategy_id, params):
        variant_params = {**params, key: variant_val}
        r = _safe_run(candles, strategy_id, variant_params, run_kwargs)
        ret = r.get("total_return")
        rows.append({
            "param": key,
            "base_value": base_val,
            "variant_value": variant_val,
            "variant_return": ret,
            "delta_pct": round(ret - base_ret, 2) if ret is not None else None,
        })
    # 判定：正收益策略中，若任一邻近参数使收益转为非正 → 参数悬崖
    cliff = base_ret > 0 and any(
        r["variant_return"] is not None and r["variant_return"] <= 0 for r in rows
    )
    return {
        "base_return": base_ret,
        "rows": rows,
        "cliff": cliff,
        "verdict": "参数敏感：邻近参数下收益转负，结果可能依赖精调" if cliff else
                   ("未发现参数悬崖（邻近参数仍为正收益）" if base_ret > 0 else "基准收益非正，敏感性检查无意义"),
    }


def oos_check(candles: list[dict], strategy_id: str, params: dict, run_kwargs: dict) -> dict[str, Any]:
    """样本内(前70%) vs 样本外(后30%)：信号全序列生成后分段评估。"""
    signals = generate_signals(strategy_id, candles, params)
    split = max(30, int(len(candles) * OOS_SPLIT))
    in_res = _safe_run(candles[:split], strategy_id, params, run_kwargs)
    # 样本外段带上前置数据作信号预热（30 根），但只从 split 起评估
    warmup = max(0, split - 30)
    oos_candles = candles[warmup:]
    oos_signals = signals[warmup:]
    try:
        oos_res = run_backtest(oos_candles, oos_signals, **run_kwargs)
    except Exception:  # noqa: BLE001
        oos_res = {}
    in_ret = in_res.get("total_return")
    oos_ret = oos_res.get("total_return")
    if in_ret is None or oos_ret is None or in_ret <= 0:
        verdict = "样本内收益非正或数据不足，无法判断稳定性"
        decay = None
    else:
        decay = round(oos_ret - in_ret, 2)
        if oos_ret < in_ret * 0.4:
            verdict = "过拟合风险高：样本外收益大幅衰减"
        elif oos_ret < in_ret * 0.75:
            verdict = "有一定衰减：样本外收益明显弱于样本内"
        else:
            verdict = "样本内外表现接近，稳健性较好"
    return {
        "split_index": split,
        "split_date": candles[split - 1]["date"] if candles else None,
        "in_sample_return": in_ret,
        "oos_sample_return": oos_ret,
        "decay_pct": decay,
        "verdict": verdict,
        "note": "样本外段含 30 根信号预热K线；结论是风险提示，不是有效性证明",
    }


def full_check(candles: list[dict], strategy_id: str, params: dict, run_kwargs: dict) -> dict:
    return {
        "sensitivity": sensitivity_check(candles, strategy_id, params, run_kwargs),
        "oos": oos_check(candles, strategy_id, params, run_kwargs),
    }
