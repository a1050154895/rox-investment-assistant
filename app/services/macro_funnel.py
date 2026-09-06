"""宏观行业漏斗：宏观状态 → 行业排序 → 行业内候选样本。

三段式过滤器（明确不是推荐器）：
1. 宏观状态：读取宏观代理矩阵（get_macro_matrix，确定性计算结果）；
2. 行业排序：显式方法论规则匹配（每条规则的行业集合与理由都是代码常量，
   思想来源登记于 docs/strategy_origins.md），叠加东财行业资金流实测数据；
3. 候选样本：目标行业的成分股按确定性因子（流通市值降序）排序。

红线：
- 行业规则是"政策敏感度的通识方法论映射"，不是实证因果，更不是涨跌预测；
- 候选池是筛选样本，输出必须携带非建议声明；
- 所有实测数据（资金流、行情）失败时诚实标注，不用规则分凑数。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.macro_data import get_macro_matrix

logger = logging.getLogger(__name__)

# 方法论规则表：dim 取宏观矩阵中的确定性量。thresholds 与矩阵自身的
# 偏强(>=65)/中性(45-64)/偏弱(<45) 分界保持一致口径。
# industries: name=展示名（含依据），boards=东财行业板块候选名（用于解析成分股）。
RULES: tuple[dict, ...] = (
    {
        "id": "fiscal_expand", "dim": "fiscal_score", "op": ">=", "threshold": 60,
        "title": "财政信用条件偏扩张",
        "rationale": "财政支出与信用扩张环境下的传统受益链",
        "industries": [
            {"name": "建筑装饰", "reason": "财政支出与基建订单直接相关", "boards": ["建筑装饰"]},
            {"name": "银行", "reason": "信用扩张环境利好信贷规模", "boards": ["银行"]},
            {"name": "建筑材料", "reason": "基建需求的上游传导", "boards": ["建筑材料"]},
        ],
    },
    {
        "id": "fiscal_contract", "dim": "fiscal_score", "op": "<=", "threshold": 45,
        "title": "财政信用条件偏收缩",
        "rationale": "财政发力不足时市场偏向防御与类债资产",
        "industries": [
            {"name": "电力行业", "reason": "现金流稳定的类债防御", "boards": ["电力行业"]},
            {"name": "煤炭", "reason": "高股息防御属性", "boards": ["煤炭行业"]},
        ],
    },
    {
        "id": "value_improve", "dim": "value_score", "op": ">=", "threshold": 60,
        "title": "价值实现改善（内需回暖）",
        "rationale": "消费与终端需求修复的受益链",
        "industries": [
            {"name": "食品饮料", "reason": "消费回暖直接受益", "boards": ["白酒", "食品饮料"]},
            {"name": "家电行业", "reason": "耐用消费弹性大", "boards": ["家电行业"]},
            {"name": "商业百货", "reason": "终端消费修复", "boards": ["商业百货"]},
        ],
    },
    {
        "id": "value_pressure", "dim": "value_score", "op": "<=", "threshold": 45,
        "title": "价值实现承压（内需偏弱）",
        "rationale": "内需偏弱时市场偏向需求刚性行业",
        "industries": [
            {"name": "电力行业", "reason": "需求刚性防御", "boards": ["电力行业"]},
            {"name": "化学制药", "reason": "医疗需求的刚性", "boards": ["化学制药"]},
        ],
    },
    {
        "id": "liquidity_loose", "dim": "m2_yoy", "op": ">=", "threshold": 8.5,
        "title": "流动性宽裕（M2 同比偏高）",
        "rationale": "宽流动性环境历史上对成长与高换手板块更友好",
        "industries": [
            {"name": "证券", "reason": "成交活跃直接受益", "boards": ["证券"]},
            {"name": "半导体", "reason": "成长股估值环境友好", "boards": ["半导体"]},
            {"name": "软件开发", "reason": "流动性敏感的成长方向", "boards": ["软件开发"]},
        ],
    },
    {
        "id": "liquidity_tight", "dim": "m2_yoy", "op": "<=", "threshold": 7.2,
        "title": "流动性偏紧（M2 同比偏低）",
        "rationale": "紧流动性环境市场偏向现金流稳定的行业",
        "industries": [
            {"name": "银行", "reason": "负债端经营优势", "boards": ["银行"]},
            {"name": "电力行业", "reason": "现金流稳定防御", "boards": ["电力行业"]},
        ],
    },
    {
        "id": "pmi_boom", "dim": "pmi", "op": ">=", "threshold": 50.5,
        "title": "制造业景气上行（PMI 高于荣枯线）",
        "rationale": "景气扩张期中游制造与电子链条订单改善",
        "industries": [
            {"name": "专用设备", "reason": "资本开支与订单改善", "boards": ["专用设备"]},
            {"name": "电子元件", "reason": "制造业景气的链条传导", "boards": ["电子元件"]},
            {"name": "化学制品", "reason": "中游需求改善", "boards": ["化学制品"]},
        ],
    },
    {
        "id": "pmi_slow", "dim": "pmi", "op": "<=", "threshold": 49.5,
        "title": "制造业景气收缩（PMI 低于荣枯线）",
        "rationale": "景气收缩期偏向需求刚性与防御",
        "industries": [
            {"name": "电力行业", "reason": "需求刚性", "boards": ["电力行业"]},
            {"name": "中药", "reason": "防御与需求刚性", "boards": ["中药"]},
        ],
    },
    {
        "id": "real_rate_low", "dim": "real_rate", "op": "<=", "threshold": 0.0,
        "title": "实质利率代理 ≤ 0（资产通胀环境）",
        "rationale": "低实质利率环境历史上利好抗通胀与定价权资产",
        "industries": [
            {"name": "贵金属", "reason": "黄金类资产的经典环境", "boards": ["贵金属"]},
            {"name": "白酒", "reason": "强定价权资产", "boards": ["白酒"]},
        ],
        "requires_calculated": True,
    },
    {
        "id": "real_rate_high", "dim": "real_rate", "op": ">=", "threshold": 2.0,
        "title": "实质利率代理偏高",
        "rationale": "高实质利率环境金融资产相对受益",
        "industries": [
            {"name": "银行", "reason": "净息差预期改善", "boards": ["银行"]},
            {"name": "保险", "reason": "投资端收益环境改善", "boards": ["保险"]},
        ],
        "requires_calculated": True,
    },
)

DISCLAIMER = (
    "漏斗输出的是筛选样本与方法论理由，不是投资建议：行业映射是通识方法论代理"
    "（非实证因果），候选池按确定性因子排序（非推荐排序），买卖决策、仓位与时点完全由用户决定。"
)


def _extract_dimensions(matrix: dict[str, Any]) -> dict[str, Any]:
    """从宏观矩阵提取漏斗需要的确定性维度值。"""
    dims: dict[str, Any] = {"fiscal_score": None, "value_score": None, "pmi": None, "m2_yoy": None}
    fiscal = matrix.get("sovereign_credit") or {}
    value = matrix.get("value_realization") or {}
    if isinstance(fiscal.get("score"), (int, float)):
        dims["fiscal_score"] = float(fiscal["score"])
    if isinstance(value.get("score"), (int, float)):
        dims["value_score"] = float(value["score"])
    for indicator in (fiscal.get("indicators") or []):
        if indicator.get("key") == "m2_yoy" and indicator.get("status") in ("available", "snapshot"):
            dims["m2_yoy"] = indicator.get("value")
        if indicator.get("key") == "pmi" and indicator.get("status") in ("available", "snapshot"):
            dims["pmi"] = indicator.get("value")
    real_rate = matrix.get("real_rate_proxy") or {}
    dims["real_rate"] = real_rate.get("value") if real_rate.get("status") == "calculated" else None
    dims["real_rate_status"] = real_rate.get("status")
    return dims


def _match(dims: dict[str, Any], rule: dict) -> bool:
    dim_value = dims.get(rule["dim"])
    if dim_value is None:
        return False
    if rule["op"] == ">=":
        return float(dim_value) >= float(rule["threshold"])
    return float(dim_value) <= float(rule["threshold"])


def evaluate_rules(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """返回命中的方法论规则及命中证据。确定性：同一矩阵输入得到同一输出。"""
    dims = _extract_dimensions(matrix)
    matched = []
    for rule in RULES:
        if rule.get("requires_calculated") and dims.get("real_rate_status") != "calculated":
            continue
        if _match(dims, rule):
            matched.append({
                "id": rule["id"], "title": rule["title"], "rationale": rule["rationale"],
                "evidence": f"{rule['dim']} = {dims.get(rule['dim'])}（阈值 {rule['op']} {rule['threshold']}）",
                "industries": rule["industries"],
            })
    return matched


def rank_industries(matched_rules: list[dict], fund_flow_rows: list[dict] | None) -> list[dict[str, Any]]:
    """行业得分 = 命中规则数（方法论匹配度）；叠加实测五日资金流作为参考列。"""
    flow_map: dict[str, dict] = {}
    for row in (fund_flow_rows or []):
        flow_map[str(row.get("sector", ""))] = row
    scores: dict[str, dict] = {}
    for rule in matched_rules:
        for entry in rule["industries"]:
            item = scores.setdefault(entry["name"], {
                "industry": entry["name"], "score": 0, "reasons": [], "boards": entry["boards"],
            })
            item["score"] += 1
            item["reasons"].append(f"{rule['title']}：{entry['reason']}")
    ranked = []
    for item in scores.values():
        flow = None
        for sector_name, row in flow_map.items():
            if item["industry"] in sector_name or sector_name in item["industry"]:
                flow = row
                break
        ranked.append({
            **item,
            "fund_flow": (flow or {}).get("flow"),
            "fund_flow_status": "realtime" if flow else "unavailable",
        })
    ranked.sort(key=lambda r: (-r["score"], r["industry"]))
    return ranked


async def _fetch_fund_flow() -> list[dict]:
    try:
        import akshare as ak
        from app.services.akshare_gate import gated_call
        frame = await asyncio.wait_for(
            gated_call(lambda: ak.stock_sector_fund_flow_rank("5", "行业")), timeout=10
        )
        rows = []
        for _, row in frame.head(60).iterrows():
            rows.append({
                "sector": str(row.get("名称", "")),
                "flow": float(row.get("主力净流入-净额", 0) or 0) / 1e8,
            })
        return rows
    except Exception as exc:
        logger.info("漏斗行业资金流不可用: %s", exc)
        return []


def _resolve_board(board_list: list[str], candidates: list[str]) -> str | None:
    for exact in candidates:
        if exact in board_list:
            return exact
    for alias in candidates:
        for board in board_list:
            if alias in board:
                return board
    return None


async def _fetch_board_list() -> list[str]:
    try:
        import akshare as ak
        from app.services.akshare_gate import gated_call
        frame = await asyncio.wait_for(gated_call(ak.stock_board_industry_name_em), timeout=10)
        return [str(v) for v in frame.iloc[:, 0].tolist()]
    except Exception as exc:
        logger.info("行业板块列表不可用: %s", exc)
        return []


async def get_funnel_ranking() -> dict[str, Any]:
    matrix = await get_macro_matrix()
    matched_rules = evaluate_rules(matrix)
    fund_flow_rows = await _fetch_fund_flow()
    ranked = rank_industries(matched_rules, fund_flow_rows)
    board_list = await _fetch_board_list()
    for item in ranked:
        resolved = _resolve_board(board_list, item.get("boards") or []) if board_list else None
        item["resolved_board"] = resolved
        item["pool_status"] = "available" if resolved else "unavailable"
        if not resolved:
            item["pool_message"] = "行业板块列表不可用或未匹配到东财板块名，候选样本暂不可得" if not board_list else "未匹配到东财板块名"
    return {
        "matrix_cell": matrix.get("matrix_cell"),
        "matrix_scores": {
            "fiscal": (matrix.get("sovereign_credit") or {}).get("score"),
            "value": (matrix.get("value_realization") or {}).get("score"),
        },
        "matched_rules": matched_rules,
        "rule_count": len(matched_rules),
        "industries": ranked,
        "data_status": "available" if ranked else "insufficient",
        "message": (
            "宏观状态未命中任何方法论规则（数据不足或处于中性区间），漏斗如实返回空排序。"
            if not ranked else "行业排序 = 方法论规则匹配 + 实测资金流参考。"
        ),
        "disclaimer": DISCLAIMER,
    }


def _parse_cap_text(value: Any) -> float:
    """从"800.35亿"这类带中文单位的文本中提取数值；无法解析记 0（排序垫底）。"""
    import re
    match = re.search(r"[\d.]+", str(value))
    return float(match.group()) if match else 0.0


async def get_candidate_pool(board: str, size: int = 8) -> dict[str, Any]:
    """目标行业的候选样本：成分股按流通市值降序（确定性因子，非推荐排序）。"""
    board = board.strip()[:20]
    try:
        import akshare as ak
        from app.services.akshare_gate import gated_call
        frame = await asyncio.wait_for(
            gated_call(lambda: ak.stock_board_industry_cons_em(symbol=board)), timeout=12
        )
    except Exception as exc:
        return {
            "board": board, "data_status": "unavailable",
            "message": f"成分股数据源不可用：{str(exc)[:120]}", "candidates": [],
            "disclaimer": DISCLAIMER,
        }
    if frame is None or frame.empty:
        return {"board": board, "data_status": "unavailable", "message": "成分股数据为空",
                "candidates": [], "disclaimer": DISCLAIMER}
    columns = {str(c): c for c in frame.columns}
    cap_col = next((c for c in columns if "流通市值" in c), None)
    code_col = next((c for c in columns if "代码" in c), None)
    name_col = next((c for c in columns if "名称" in c), None)
    price_col = next((c for c in columns if "最新价" in c), None)
    cap_sorted = frame
    if cap_col:
        cap_sorted = frame.copy()
        cap_sorted["_cap"] = cap_sorted[cap_col].apply(_parse_cap_text)
        cap_sorted = cap_sorted.sort_values("_cap", ascending=False)
    candidates = []
    for _, row in cap_sorted.head(max(1, min(size, 30))).iterrows():
        candidates.append({
            "code": str(row.get(code_col)) if code_col else "",
            "name": str(row.get(name_col)) if name_col else "",
            "price": row.get(price_col) if price_col else None,
            "market_cap_text": str(row.get(cap_col)) if cap_col else "",
        })
    return {
        "board": board,
        "data_status": "realtime",
        "sort_factor": "流通市值降序（确定性因子，非推荐排序）",
        "candidates": candidates,
        "disclaimer": DISCLAIMER,
    }
