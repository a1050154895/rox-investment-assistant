"""决策日志 API — CRUD + 统计 + 复盘"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

# 临时单用户内存存储。生产环境不预置虚构交易数据；下一阶段迁移 PostgreSQL。
_journal: list[dict] = []
_next_id = 1


class DecisionCreate(BaseModel):
    stock: str = Field(..., max_length=20)
    code: str = Field(..., max_length=10)
    action: str = Field(..., description="买入/卖出/持有/减仓")
    stage: str = Field(..., description="试仓30%/确认30%/主力40%")
    cycle_stage: str = Field("流转", description="积累/集中/流转/分配/再生产")
    contradiction_intensity: int = Field(50, ge=0, le=100)
    value_realization: int = Field(50, ge=0, le=100)
    consistency_score: int = Field(50, ge=0, le=100)
    reason: str = Field("", max_length=500)


class DecisionUpdate(BaseModel):
    result: Optional[str] = None
    result_pct: Optional[float] = None
    review: Optional[str] = None


@router.get("/")
async def list_decisions(
    action: str = Query("", description="筛选操作类型"),
    limit: int = Query(50, ge=1, le=200),
):
    """查询决策列表"""
    results = _journal
    if action:
        results = [d for d in results if d["action"] == action]
    results = sorted(results, key=lambda x: x["date"], reverse=True)
    return {"total": len(results), "decisions": results[:limit]}


@router.post("/")
async def create_decision(decision: DecisionCreate):
    """创建决策记录"""
    global _next_id
    entry = {
        "id": _next_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "result": "待观察",
        "result_pct": None,
        "holding_days": 0,
        "review": None,
        **decision.model_dump(),
    }
    _journal.insert(0, entry)
    _next_id += 1
    return {"success": True, "id": entry["id"], "decision": entry}


@router.get("/{decision_id}")
async def get_decision(decision_id: int):
    """获取单条决策详情"""
    for d in _journal:
        if d["id"] == decision_id:
            return d
    return {"error": "未找到该决策记录"}


@router.put("/{decision_id}")
async def update_decision(decision_id: int, update: DecisionUpdate):
    """更新决策记录（补充事后结果/复盘）"""
    for d in _journal:
        if d["id"] == decision_id:
            if update.result is not None:
                d["result"] = update.result
            if update.result_pct is not None:
                d["result_pct"] = update.result_pct
            if update.review is not None:
                d["review"] = update.review
            return {"success": True, "decision": d}
    return {"error": "未找到该决策记录"}


@router.delete("/{decision_id}")
async def delete_decision(decision_id: int):
    """删除决策记录"""
    global _journal
    before = len(_journal)
    _journal = [d for d in _journal if d["id"] != decision_id]
    if len(_journal) < before:
        return {"success": True}
    return {"error": "未找到该决策记录"}


@router.get("/stats/summary")
async def stats_summary():
    """统计概览"""
    total = len(_journal)
    scored = [d for d in _journal if d["consistency_score"]]
    avg_score = round(sum(d["consistency_score"] for d in scored) / max(len(scored), 1), 1)
    high_consistency = len([d for d in _journal if d["consistency_score"] >= 70])
    compliance_rate = round(high_consistency / max(total, 1) * 100, 1)

    wins = [d for d in _journal if d["result"] == "盈"]
    losses = [d for d in _journal if d["result"] == "亏"]
    win_rate = round(len(wins) / max(len(wins) + len(losses), 1) * 100, 1)

    low_score = [d for d in _journal if d["consistency_score"] < 60]
    error_patterns = "存在低一致性记录，请逐条复核证据与纪律" if low_score else "暂无足够样本识别错误模式"

    return {
        "total": total,
        "avg_consistency": avg_score,
        "compliance_rate": compliance_rate,
        "win_rate": win_rate,
        "wins": len(wins),
        "losses": len(losses),
        "pending": len([d for d in _journal if d["result"] == "待观察"]),
        "common_error": error_patterns,
        "score_distribution": {
            "high": len([d for d in _journal if d["consistency_score"] >= 75]),
            "medium": len([d for d in _journal if 45 <= d["consistency_score"] < 75]),
            "low": len([d for d in _journal if d["consistency_score"] < 45]),
        }
    }


@router.post("/review")
async def generate_review(
    start_date: str = Query("2026-07-01"),
    end_date: str = Query("2026-07-31"),
):
    """生成复盘报告"""
    decisions = [d for d in _journal if start_date <= d["date"] <= end_date]
    total = len(decisions)
    wins = [d for d in decisions if d["result"] == "盈"]
    losses = [d for d in decisions if d["result"] == "亏"]
    avg_score = round(sum(d["consistency_score"] for d in decisions) / max(total, 1), 1)

    # 按周期阶段分组统计
    stage_stats = {}
    for d in decisions:
        stage = d["cycle_stage"]
        if stage not in stage_stats:
            stage_stats[stage] = {"count": 0, "wins": 0, "avg_score": 0, "scores": []}
        stage_stats[stage]["count"] += 1
        if d["result"] == "盈":
            stage_stats[stage]["wins"] += 1
        stage_stats[stage]["scores"].append(d["consistency_score"])

    for s in stage_stats.values():
        s["avg_score"] = round(sum(s["scores"]) / max(len(s["scores"]), 1), 1)
        s["win_rate"] = round(s["wins"] / max(s["count"], 1) * 100, 1)
        del s["scores"]

    return {
        "period": f"{start_date} ~ {end_date}",
        "total_decisions": total,
        "wins": len(wins),
        "losses": len(losses),
        "pending": total - len(wins) - len(losses),
        "avg_consistency": avg_score,
        "total_return": round(sum(d.get("result_pct", 0) or 0 for d in decisions), 2),
        "stage_breakdown": stage_stats,
        "insights": ["当前样本不足，无法得出稳定胜率或阶段有效性结论"] if total < 10 else [
            "请结合样本量、市场环境和最大回撤评估框架表现",
            "一致性评分只反映纪律匹配，不代表未来收益",
        ],
        "suggestions": [
            "持续记录事实依据、数据来源、建仓触发和退出条件",
            "至少积累10条已完成决策后再评估统计结果",
        ]
    }
