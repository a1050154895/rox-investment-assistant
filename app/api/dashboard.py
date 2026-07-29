"""仪表盘聚合 API — 一次请求返回宏观+周期+矛盾+334+自选概览"""
import random
from datetime import datetime, timedelta
from fastapi import APIRouter

router = APIRouter()


@router.get("/overview")
async def overview():
    """仪表盘聚合数据"""
    return {
        "market_indices": [
            {"name": "上证指数", "code": "000001.SH", "price": 3289.47, "change": 1.23, "change_pct": 0.04},
            {"name": "深证成指", "code": "399001.SZ", "price": 10457.82, "change": -15.36, "change_pct": -0.15},
            {"name": "创业板指", "code": "399006.SZ", "price": 2156.33, "change": 8.91, "change_pct": 0.41},
            {"name": "沪深300", "code": "000300.SH", "price": 3842.16, "change": 5.67, "change_pct": 0.15},
        ],
        "macro_compass": {
            "sovereign_credit": {"status": "平衡", "score": 62, "trend": "stable",
                                 "detail": "财政纪律中等，直接税占比缓慢提升"},
            "value_realization": {"status": "中", "score": 55, "trend": "up",
                                  "detail": "社会总资本周转率回升，消费端温和复苏"},
            "framework_advice": "当前处于资本周期「流转」阶段中期，建议维持核心30%仓位不变，关注主力资金持续流入的周期股。"
        },
        "capital_cycle": {
            "stages": ["积累", "集中", "流转", "分配", "再生产"],
            "current_stage": 2,
            "stage_name": "流转",
            "stage_detail": "资本从金融体系向实体经济流转加速，产业资本活跃度提升",
            "progress": 45
        },
        "contradictions": {
            "primary": {"name": "扩大内需 vs 居民收入增长放缓", "intensity": 72, "trend": "up"},
            "secondary": {"name": "产业升级 vs 传统产能出清", "intensity": 58, "trend": "stable"},
            "tertiary": {"name": "直接融资 vs 间接融资结构", "intensity": 41, "trend": "down"},
        },
        "discipline_334": {
            "core": {"target": 30, "actual": 28, "stocks": ["贵州茅台", "宁德时代", "招商银行"]},
            "satellite": {"target": 30, "actual": 22, "stocks": ["中际旭创", "北方华创"]},
            "cash": {"target": 40, "actual": 50, "note": "现金比例偏高，可适度加仓卫星池"},
            "advice": "现金50% > 基准40%，建议在流转阶段将10%现金转入卫星池，关注资金流入确认的标的。"
        },
        "watchlist": [
            {"name": "贵州茅台", "code": "600519", "price": 1689.50, "change_pct": 0.82,
             "score": 78, "score_label": "较高"},
            {"name": "宁德时代", "code": "300750", "price": 182.30, "change_pct": -1.15,
             "score": 65, "score_label": "中等"},
            {"name": "中际旭创", "code": "300308", "price": 156.80, "change_pct": 3.27,
             "score": 85, "score_label": "高"},
            {"name": "招商银行", "code": "600036", "price": 35.42, "change_pct": 0.28,
             "score": 71, "score_label": "较高"},
            {"name": "北方华创", "code": "002371", "price": 312.60, "change_pct": 2.14,
             "score": 80, "score_label": "高"},
        ],
        "recent_decisions": [
            {"stock": "中际旭创", "code": "300308", "action": "买入", "date": "2026-07-28",
             "stage": "确认30%", "score": 85, "result": "待观察"},
            {"stock": "贵州茅台", "code": "600519", "action": "持有", "date": "2026-07-25",
             "stage": "主力40%", "score": 78, "result": "+2.3%"},
            {"stock": "宁德时代", "code": "300750", "action": "减仓", "date": "2026-07-22",
             "stage": "确认30%", "score": 52, "result": "-1.5%"},
        ],
        "updated_at": datetime.now().isoformat(),
    }


@router.get("/market_heatmap")
async def market_heatmap():
    """市场热力图数据"""
    sectors = [
        "半导体", "白酒", "银行", "新能源", "医药", "军工", "计算机",
        "房地产", "有色金属", "化工", "传媒", "电力", "汽车", "食品饮料",
        "家电", "钢铁", "建材", "农业", "通信", "券商"
    ]
    data = []
    for s in sectors:
        change = round(random.uniform(-3.5, 3.5), 2)
        data.append({"sector": s, "change": change, "volume": random.randint(50, 500)})
    return {"sectors": data}
