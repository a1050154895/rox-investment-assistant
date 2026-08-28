"""ROX 宏观资讯研判服务。

所有研判均为公开信息的结构化观察，不构成投资建议。服务优先尝试 AKShare
公开资讯接口；在数据源不可用时使用带来源和日期的演示快照，保证 Render 上
页面与 API 具备稳定降级能力。
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from app.services.resilience import CircuitBreaker

logger = logging.getLogger(__name__)
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 300

_NEWS_BREAKER = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
_FLOW_BREAKER = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
FALLBACK_NEWS = [
    {"id": "policy-fiscal", "category": "政策", "title": "财政与促消费政策的落地节奏仍是内需行业预期差的核心变量", "source": "公开政策信息整理", "published_at": "2026-07-30T08:30:00", "impact": "中性偏多", "direction": "positive", "channels": ["消费", "基建", "金融"], "evidence": "需持续核验政策细则、预算执行和终端需求数据", "fact_or_view": "研判"},
    {"id": "global-energy", "category": "全球宏观", "title": "能源与航运价格波动需通过成本端传导关注化工、运输与出口链", "source": "公开市场数据整理", "published_at": "2026-07-30T07:45:00", "impact": "风险观察", "direction": "warning", "channels": ["能源", "化工", "航运"], "evidence": "观察原油、运价与企业毛利率的同步性", "fact_or_view": "研判"},
    {"id": "industry-ai", "category": "产业链", "title": "算力投资与通信设备订单验证，需结合资本开支和资金流确认", "source": "上市公司公告与行业公开信息", "published_at": "2026-07-29T18:20:00", "impact": "结构性机会", "direction": "positive", "channels": ["通信", "半导体", "计算机"], "evidence": "订单、营收增速、库存和主力资金需至少两项共振", "fact_or_view": "研判"},
    {"id": "liquidity", "category": "资金流", "title": "增量资金与成交结构分化，避免将单日资金异动视为趋势确认", "source": "公开行情数据整理", "published_at": "2026-07-29T16:00:00", "impact": "中性", "direction": "neutral", "channels": ["全市场"], "evidence": "以五日净流、成交额和行业扩散度交叉确认", "fact_or_view": "研判"},
]

GLOBAL_RISK = [
    {"factor": "全球增长", "status": "观察", "score": 54, "direction": "neutral", "transmission": "外需订单 → 出口链利润 → 制造业资本开支", "watch": "主要经济体制造业、出口新订单"},
    {"factor": "利率与汇率", "status": "观察", "score": 58, "direction": "warning", "transmission": "无风险利率 → 估值折现 → 成长股风险偏好", "watch": "美元指数、国债收益率、人民币汇率"},
    {"factor": "能源与航运", "status": "风险观察", "score": 66, "direction": "warning", "transmission": "原料与运价 → 成本端 → 化工/运输/出口毛利", "watch": "原油、煤炭、集运运价"},
    {"factor": "供应链景气", "status": "结构改善", "score": 63, "direction": "positive", "transmission": "订单 → 库存 → 产能利用率 → 企业盈利", "watch": "半导体、通信、新能源订单与库存"},
]

POLICY_TRACKER = [
    {"topic": "扩内需与消费", "stage": "执行观察", "affected": ["食品饮料", "家电", "商贸零售"], "signal": "正向", "method": "跟踪细则、社零、企业订单和估值变化"},
    {"topic": "科技与自主可控", "stage": "产业验证", "affected": ["半导体", "通信设备", "计算机"], "signal": "结构性", "method": "跟踪资本开支、订单、国产替代份额与资金流"},
    {"topic": "稳增长与基建", "stage": "项目落地观察", "affected": ["建筑", "建材", "工程机械"], "signal": "中性偏多", "method": "跟踪财政支出、项目开工和商品需求"},
]

SECTOR_FLOW = [
    {"sector": "半导体", "flow": 3.8, "trend": "inflow", "driver": "政策预期 + 产业订单验证"},
    {"sector": "通信设备", "flow": 2.6, "trend": "inflow", "driver": "算力链订单与资金共振"},
    {"sector": "银行", "flow": 1.2, "trend": "inflow", "driver": "高股息防御与估值修复"},
    {"sector": "白酒", "flow": -0.8, "trend": "outflow", "driver": "消费数据与估值消化"},
    {"sector": "新能源", "flow": -1.5, "trend": "outflow", "driver": "供需与价格压力待确认"},
]


def _normalize_news(frame: Any, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    columns = [str(c) for c in frame.columns]
    for index, (_, row) in enumerate(frame.head(limit).iterrows()):
        title = str(row.get("标题") or row.get("新闻标题") or "").strip()
        # 财联社空标题：从"内容"或"摘要"提取前30字作为标题
        if not title or title == "nan":
            content = str(row.get("内容") or row.get("摘要") or "").strip()
            if content and content != "nan":
                # 去掉"财联社X月X日电，"前缀
                for prefix_len in range(15, 5, -1):
                    if content.startswith("财联社") and "电" in content[:prefix_len]:
                        content = content[content.index("电") + 1:].strip()
                        break
                title = content[:40] + ("..." if len(content) > 40 else "")
            else:
                title = "市场资讯"
        # 简单分类
        category = "市场资讯"
        for kw, cat in [("降息", "货币政策"), ("利率", "货币政策"), ("PMI", "宏观"), ("CPI", "宏观"),
                         ("GDP", "宏观"), ("财政", "财政"), ("税", "财政"), ("政策", "政策"),
                         ("芯片", "科技"), ("半导体", "科技"), ("AI", "科技"), ("人工智能", "科技"),
                         ("新能源", "新能源"), ("锂", "新能源"), ("光伏", "新能源"),
                         ("消费", "消费"), ("白酒", "消费"), ("食品", "消费")]:
            if kw in title:
                category = cat
                break
        source = str(row.get("文章来源") or row.get("来源") or "公开资讯")
        if source == "nan":
            source = "公开资讯"
        pub_date = str(row.get("发布日期") or row.get("发布时间") or "")
        if pub_date == "nan":
            pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        items.append({
            "id": f"live-{index}", "category": category, "title": title,
            "source": source, "published_at": pub_date,
            "impact": "待研判", "direction": "neutral", "channels": ["需人工归类"],
            "evidence": "原始资讯仅提供事实线索，需结合数据验证", "fact_or_view": "事实线索",
        })
    return items


def _dedup_news(news: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按标准化标题去重：完全一致的资讯只保留一条。"""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in news:
        key = str(item.get("title", "")).strip().lower().replace(" ", "")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


async def _fetch_news_akshare() -> tuple[list[dict[str, Any]], str]:
    """尝试多个 AKShare 资讯接口，返回 (news, source_status)。"""
    if _NEWS_BREAKER.is_open:
        logger.info("资讯源熔断中，跳过 AKShare 调用")
        return [], ""
    sources = [
        ("stock_info_global_em", None, "AKShare / 东方财富公开资讯"),
        ("stock_info_global_cls", "财经", "AKShare / 财联社公开资讯"),
        ("stock_info_global_sina", None, "AKShare / 新浪财经公开资讯"),
    ]
    for func_name, arg, label in sources:
        try:
            import akshare as ak
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            from app.services.akshare_gate import gated_call
            if arg:
                frame = await asyncio.wait_for(gated_call(lambda: func(arg)), timeout=8)
            else:
                frame = await asyncio.wait_for(gated_call(func), timeout=8)
            if frame is not None and not frame.empty:
                _NEWS_BREAKER.record_success()
                return _normalize_news(frame, 10), label
        except Exception as exc:
            logger.info("资讯源 %s 不可用: %s", func_name, exc)
            continue
    _NEWS_BREAKER.record_failure()
    return [], ""


async def _get_intelligence_brief_raw(force: bool = False) -> dict[str, Any]:
    """返回资讯、政策、全球风险和行业资金研判面板。"""
    cache_key = "brief"
    cached = _CACHE.get(cache_key)
    if cached and not force and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    news, source_status = await _fetch_news_akshare()
    if not news:
        news = FALLBACK_NEWS
        source_status = "公开信息结构化快照（AKShare 资讯源暂不可用）"
    news = _dedup_news(news)

    # 尝试获取实时行业资金流
    sector_flow = SECTOR_FLOW
    flow_status = "结构化快照"
    try:
        import akshare as ak
        from app.services.akshare_gate import gated_call
        flow_frame = await asyncio.wait_for(
            gated_call(lambda: ak.stock_sector_fund_flow_rank("5", "行业")),
            timeout=8
        )
        if flow_frame is not None and not flow_frame.empty:
            live_flow = []
            for _, row in flow_frame.head(8).iterrows():
                live_flow.append({
                    "sector": str(row.get("名称", "")),
                    "flow": float(row.get("主力净流入-净额", 0) or 0) / 1e8,
                    "trend": "inflow" if float(row.get("主力净流入-净额", 0) or 0) > 0 else "outflow",
                    "driver": str(row.get("主力净流入-净占比", "")) + "% | 5日累计",
                })
            if live_flow:
                sector_flow = live_flow
                flow_status = "AKShare / 东方财富行业资金流（5日）"
    except Exception as exc:
        logger.info("行业资金流源不可用: %s", exc)

    result = {
        "disclaimer": "本页聚合公开资讯与结构化研判，非投资建议。研判须与行情、财务和仓位纪律交叉验证。",
        "source_status": source_status,
        "flow_status": flow_status,
        "news": news,
        "global_risk": GLOBAL_RISK,
        "policy_tracker": POLICY_TRACKER,
        "sector_flow": sector_flow,
        "method": [
            "先区分事实线索与观点，不把标题当结论。",
            "用政策细则、宏观数据、行业订单与资金流至少两项交叉验证。",
            "将全球变量通过利率、汇率、能源、贸易和供应链映射到行业盈利。",
            "任何单一事件不得绕过 334 仓位纪律与风险控制。",
        ],
        "updated_at": datetime.now().isoformat(),
    }
    _CACHE[cache_key] = (time.time(), result)
    return result


async def get_stock_intelligence(code: str, name: str, industry: str) -> dict[str, Any]:
    """将宏观资讯映射到单个股票的行业传导路径。"""
    brief = await get_intelligence_brief()
    relevant = [item for item in brief["news"] if industry and industry in item.get("channels", [])]
    if not relevant:
        relevant = brief["news"][:3]
    sector = next((item for item in brief["sector_flow"] if item["sector"] == industry), None)
    return {
        "code": code, "name": name, "industry": industry,
        "news": relevant[:3], "sector_flow": sector,
        "transmission": f"全球宏观/政策 → {industry or '所属行业'}景气与成本 → {name}订单、毛利与估值",
        "rule": "资讯只作为假设生成器；需以业绩、订单、价格趋势与资金流至少两项验证后再纳入决策。",
        "updated_at": brief["updated_at"],
    }


# ---- DataSourceRegistry 埋点 ----
from app.services import data_source_registry as _registry  # noqa: E402


async def get_intelligence_brief(force: bool = False) -> dict[str, Any]:
    result = await _get_intelligence_brief_raw(force)
    ok = bool(result.get("news") or result.get("sector_flow"))
    _registry.record("akshare_news", ok=ok, error=None if ok else "资讯抓取为空")
    return result
