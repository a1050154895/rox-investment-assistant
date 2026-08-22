"""情报主题主线：把资讯聚成可追踪的事件主题。

设计原则：
- 只做规则式聚类（关键词/类别/时间），不做情绪打分，不输出涨跌预测；
- 每个主题带时间线（起因→发展→当前）、影响行业和验证问题；
- 排序依据是"研究关联度 + 时效 + 主题规模"，全部可解释。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# 主题定义：关键词命中即归入；顺序即优先级
THEME_RULES: list[dict[str, Any]] = [
    {"id": "rates-liquidity", "name": "利率与流动性", "keywords": ["降息", "加息", "利率", "央行", "美联储", "流动性", "LPR", "国债"],
     "industries": ["银行", "证券", "成长股估值"], "verify": "政策利率与市场利率是否同步下移；社融与成交额是否配合"},
    {"id": "algo-semi", "name": "算力与半导体", "keywords": ["芯片", "半导体", "AI", "人工智能", "算力", "光模块", "存储", "晶圆"],
     "industries": ["半导体", "通信设备", "计算机"], "verify": "资本开支、订单与库存周期是否共振；国产替代份额变化"},
    {"id": "trade-external", "name": "贸易与外部变量", "keywords": ["关税", "贸易", "出口", "制裁", "汇率", "外需"],
     "industries": ["出口链", "化工", "航运"], "verify": "出口新订单与运价、汇率方向是否一致"},
    {"id": "new-energy", "name": "新能源供需", "keywords": ["新能源", "锂", "光伏", "储能", "电池", "硅料", "碳酸锂"],
     "industries": ["电力设备", "有色"], "verify": "产品价格是否企稳；供需缺口与排产数据"},
    {"id": "consumption", "name": "消费与内需", "keywords": ["消费", "白酒", "食品", "零售", "免税", "促消费", "内需"],
     "industries": ["食品饮料", "商贸零售", "家电"], "verify": "社零与终端价格、企业订单是否同步改善"},
    {"id": "fiscal-policy", "name": "财政与政策落地", "keywords": ["财政", "专项债", "税", "政策", "基建", "政府投资"],
     "industries": ["建筑", "建材", "工程机械"], "verify": "财政支出节奏、项目开工与商品需求"},
    {"id": "property", "name": "地产链", "keywords": ["地产", "房地产", "房价", "房贷", "竣工", "土地"],
     "industries": ["房地产", "家居", "建材"], "verify": "销售面积与价格、竣工和家居订单"},
    {"id": "energy-cost", "name": "能源与成本", "keywords": ["原油", "油价", "煤炭", "天然气", "运价", "航运", "能源"],
     "industries": ["化工", "运输", "煤炭"], "verify": "成本端价格向中游毛利的传导幅度"},
]

# 突发识别：时间窗口内 + 关键词，只标注"需要立即核对"，不给涨跌判断
BREAKING_WINDOW_HOURS = 36
BREAKING_KEYWORDS = ("降息", "加息", "关税", "制裁", "暂停", "突发", "紧急", "爆雷", "退市", "业绩预告", "重大合同", "战争", "地缘")


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    candidates = {
        "%Y-%m-%d %H:%M": text[:16] if ":" in text and "T" not in text else None,
        "%Y-%m-%dT%H:%M:%S": text[:19] if "T" in text and "." not in text else None,
        "%Y-%m-%dT%H:%M:%S.%f": text[:26] if "." in text else None,
        "%Y-%m-%d": text[:10],
    }
    for fmt, value in candidates.items():
        if not value:
            continue
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _hours_ago(value: Any) -> float | None:
    parsed = _parse_time(value)
    if not parsed:
        return None
    delta = datetime.now() - parsed
    return delta.total_seconds() / 3600


def is_breaking(item: dict[str, Any], now: datetime | None = None) -> bool:
    hours = _hours_ago(item.get("published_at"))
    if hours is None or hours < 0 or hours > BREAKING_WINDOW_HOURS:
        return False
    title = str(item.get("title", ""))
    return any(kw in title for kw in BREAKING_KEYWORDS)


def _match_theme(item: dict[str, Any]) -> dict[str, Any] | None:
    text = str(item.get("title", "")) + " " + str(item.get("evidence", ""))
    for rule in THEME_RULES:
        if any(kw in text for kw in rule["keywords"]):
            return rule
    return None


def _importance(theme: dict[str, Any]) -> float:
    """主题重要度 = 规模 + 时效 + 类别权重；只用于排序，不用于结论。"""
    size = min(theme.get("count", 0), 5) / 5
    newest = theme.get("newest_hours")
    recency = max(0.0, 1 - newest / 48) if newest is not None else 0.0
    weight = 1.2 if theme.get("rule", {}).get("id") in ("rates-liquidity", "fiscal-policy", "trade-external") else 1.0
    return round((0.5 * size + 0.5 * recency) * weight, 3)


def build_themes(
    news: list[dict[str, Any]],
    policy_tracker: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """把资讯聚成主题主线；未命中规则的单条资讯归入其自身类别。"""
    buckets: dict[str, dict[str, Any]] = {}
    for item in news:
        rule = _match_theme(item)
        key = rule["id"] if rule else f"cat:{item.get('category', '市场资讯')}"
        if key not in buckets:
            name = rule["name"] if rule else str(item.get("category", "市场资讯"))
            industries = list(rule["industries"]) if rule else []
            verify = rule["verify"] if rule else "该类别资讯分散，逐条核对来源与日期"
            buckets[key] = {"id": key, "name": name, "news": [], "industries": set(industries),
                            "verify": verify, "rule": rule or {"id": key}}
        buckets[key]["news"].append(item)
        for channel in item.get("channels", []):
            if channel and channel != "需人工归类":
                buckets[key]["industries"].add(str(channel))

    themes = []
    for bucket in buckets.values():
        timeline = sorted(bucket["news"], key=lambda x: str(x.get("published_at", "")))
        newest = _hours_ago(timeline[-1].get("published_at")) if timeline else None
        themes.append({
            "id": bucket["id"],
            "name": bucket["name"],
            "timeline": timeline,
            "count": len(timeline),
            "industries": sorted(bucket["industries"]),
            "verify_question": bucket["verify"],
            "newest_hours": round(newest, 1) if newest is not None else None,
            "has_breaking": any(is_breaking(i) for i in timeline),
        })  # noqa: E501
    for theme in themes:
        theme["importance"] = _importance(theme)
    themes.sort(key=lambda t: (t["has_breaking"], t["importance"]), reverse=True)

    if policy_tracker:
        for tracker in policy_tracker:
            for industry in tracker.get("affected", []):
                for theme in themes:
                    if industry in theme["industries"]:
                        theme.setdefault("policy_topics", []).append(tracker["topic"])
    return themes


def mark_breaking(news: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """给资讯打突发标记并置顶排序；非突发的保持原顺序。"""
    for item in news:
        item["is_breaking"] = is_breaking(item)
    return sorted(news, key=lambda x: not x["is_breaking"])


def _related_names(cards: list[dict[str, Any]], watchlist: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """用户研究对象集合：(名称, 类型)。"""
    names: list[tuple[str, str]] = []
    for card in cards or []:
        if card.get("stock"):
            names.append((str(card["stock"]), "研究卡"))
    for w in watchlist or []:
        name = w.get("price_name") or w.get("name")
        if name:
            names.append((str(name), "自选"))
    return names


def rank_for_user(
    themes: list[dict[str, Any]],
    news: list[dict[str, Any]],
    cards: list[dict[str, Any]] | None = None,
    watchlist: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """按研究关联度排序：命中用户研究对象的优先，其次突发，其次重要度。"""
    targets = _related_names(cards or [], watchlist or [])
    target_names = [name for name, _ in targets]

    def theme_hit(theme: dict[str, Any]) -> int:
        hits = 0
        for name in target_names:
            for item in theme["timeline"]:
                if name and name in str(item.get("title", "")):
                    hits += 1
                    break
        return hits

    for theme in themes:
        theme["research_hits"] = theme_hit(theme)
    themes.sort(key=lambda t: (t["research_hits"], t["has_breaking"], t["importance"]), reverse=True)

    for item in news:
        item["research_relevant"] = [name for name in target_names if name and name in str(item.get("title", ""))]
    news.sort(key=lambda x: (bool(x["research_relevant"]), x.get("is_breaking", False)), reverse=True)

    return {
        "themes": themes,
        "news": news,
        "matched_targets": sorted({f"{name}（{kind}）" for name, kind in targets}),
        "sort_rule": "研究关联度 → 突发 → 主题重要度；重要度=规模+时效+类别权重，无情绪分",
    }
