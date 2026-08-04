"""ROX 选股引擎 — 基于腾讯行情批量快照的多条件筛选。

定位：研究辅助工具，帮助用户从预设股票池中按财务/行情条件筛选，
不输出买卖建议。筛选结果须结合个股透视、334 纪律与宏观矩阵交叉验证。
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.tencent_data import fetch_quotes

logger = logging.getLogger(__name__)

# ============ 预设股票池（覆盖主要行业，约 80 只热门 A 股） ============

STOCK_POOL: list[dict[str, str]] = [
    # 白酒/消费
    {"code": "600519", "name": "贵州茅台", "industry": "白酒"},
    {"code": "000858", "name": "五粮液", "industry": "白酒"},
    {"code": "000568", "name": "泸州老窖", "industry": "白酒"},
    {"code": "600809", "name": "山西汾酒", "industry": "白酒"},
    # 银行/金融
    {"code": "600036", "name": "招商银行", "industry": "银行"},
    {"code": "601398", "name": "工商银行", "industry": "银行"},
    {"code": "601318", "name": "中国平安", "industry": "保险"},
    {"code": "601166", "name": "兴业银行", "industry": "银行"},
    {"code": "600000", "name": "浦发银行", "industry": "银行"},
    {"code": "601628", "name": "中国人寿", "industry": "保险"},
    # 半导体/科技
    {"code": "002371", "name": "北方华创", "industry": "半导体"},
    {"code": "688981", "name": "中芯国际", "industry": "半导体"},
    {"code": "002049", "name": "紫光国微", "industry": "半导体"},
    {"code": "300308", "name": "中际旭创", "industry": "通信设备"},
    {"code": "002415", "name": "海康威视", "industry": "计算机"},
    {"code": "000063", "name": "中兴通讯", "industry": "通信设备"},
    {"code": "600519", "name": "贵州茅台", "industry": "白酒"},
    {"code": "300059", "name": "东方财富", "industry": "证券"},
    {"code": "600276", "name": "恒瑞医药", "industry": "医药"},
    # 新能源/电力
    {"code": "300750", "name": "宁德时代", "industry": "电池"},
    {"code": "002594", "name": "比亚迪", "industry": "乘用车"},
    {"code": "601012", "name": "隆基绿能", "industry": "新能源"},
    {"code": "600900", "name": "长江电力", "industry": "电力"},
    {"code": "601985", "name": "中国核电", "industry": "电力"},
    {"code": "600886", "name": "国投电力", "industry": "电力"},
    # 消费/零售
    {"code": "600887", "name": "伊利股份", "industry": "食品"},
    {"code": "000651", "name": "格力电器", "industry": "家电"},
    {"code": "000333", "name": "美的集团", "industry": "家电"},
    {"code": "600066", "name": "宇通客车", "industry": "汽车"},
    # 医药
    {"code": "300015", "name": "爱尔眼科", "industry": "医药"},
    {"code": "600436", "name": "片仔癀", "industry": "医药"},
    {"code": "000538", "name": "云南白药", "industry": "医药"},
    # 化工/材料
    {"code": "600309", "name": "万华化学", "industry": "化工"},
    {"code": "601111", "name": "中国国航", "industry": "航空"},
    # 军工
    {"code": "600760", "name": "中航沈飞", "industry": "军工"},
    {"code": "000768", "name": "中航西飞", "industry": "军工"},
    # 基建/资源
    {"code": "601088", "name": "中国神华", "industry": "煤炭"},
    {"code": "601899", "name": "紫金矿业", "industry": "有色"},
    {"code": "600585", "name": "海螺水泥", "industry": "建材"},
    {"code": "601668", "name": "中国建筑", "industry": "建筑"},
    # 通信/传媒
    {"code": "600050", "name": "中国联通", "industry": "通信"},
    {"code": "002027", "name": "分众传媒", "industry": "传媒"},
    # 物流
    {"code": "600029", "name": "南方航空", "industry": "航空"},
    {"code": "601021", "name": "春秋航空", "industry": "航空"},
    # 房地产
    {"code": "000002", "name": "万科A", "industry": "房地产"},
    {"code": "600048", "name": "保利发展", "industry": "房地产"},
    # 农业
    {"code": "000876", "name": "新希望", "industry": "农业"},
    # 电气
    {"code": "600406", "name": "国电南瑞", "industry": "电气"},
    {"code": "002241", "name": "歌尔股份", "industry": "电子"},
    {"code": "603259", "name": "药明康德", "industry": "医药"},
    {"code": "300760", "name": "迈瑞医疗", "industry": "医疗器械"},
    {"code": "600346", "name": "恒力石化", "industry": "化工"},
    {"code": "601618", "name": "中国中冶", "industry": "建筑"},
    {"code": "601857", "name": "中国石油", "industry": "石油"},
    {"code": "600028", "name": "中国石化", "industry": "石油"},
    {"code": "600019", "name": "宝钢股份", "industry": "钢铁"},
    {"code": "000725", "name": "京东方A", "industry": "电子"},
    {"code": "603501", "name": "韦尔股份", "industry": "半导体"},
    {"code": "002475", "name": "立讯精密", "industry": "电子"},
    {"code": "300124", "name": "汇川技术", "industry": "电气"},
    {"code": "600031", "name": "三一重工", "industry": "机械"},
    {"code": "000157", "name": "中联重科", "industry": "机械"},
    {"code": "600009", "name": "上海机场", "industry": "交通"},
    {"code": "601111", "name": "中国国航", "industry": "航空"},
    {"code": "002714", "name": "牧原股份", "industry": "农业"},
    {"code": "600690", "name": "海尔智家", "industry": "家电"},
    {"code": "603288", "name": "海天味业", "industry": "食品"},
    {"code": "600660", "name": "福耀玻璃", "industry": "汽车"},
    {"code": "002179", "name": "中航光电", "industry": "军工"},
    {"code": "600862", "name": "中航高科", "industry": "军工"},
    {"code": "300394", "name": "天孚通信", "industry": "通信"},
    {"code": "300502", "name": "新易盛", "industry": "通信"},
    {"code": "688256", "name": "寒武纪", "industry": "半导体"},
]

# 去重
_seen = set()
_pool_unique: list[dict[str, str]] = []
for _s in STOCK_POOL:
    if _s["code"] not in _seen:
        _seen.add(_s["code"])
        _pool_unique.append(_s)
STOCK_POOL = _pool_unique

# ============ 预设策略 ============

PRESETS: list[dict[str, Any]] = [
    {
        "id": "low_pe",
        "name": "低估值",
        "description": "PE < 20 且 PB < 3，适合价值型研究",
        "filters": {"pe_max": 20, "pb_max": 3},
    },
    {
        "id": "high_dividend",
        "name": "高股息蓝筹",
        "description": "市值 > 3000 亿且 PE < 15，稳健型标的",
        "filters": {"market_cap_min": 3000, "pe_max": 15},
    },
    {
        "id": "hot_active",
        "name": "活跃交易",
        "description": "换手率 > 1%，近期交投活跃",
        "filters": {"turnover_min": 1.0},
    },
    {
        "id": "growth_mid",
        "name": "中等市值成长",
        "description": "市值 500-5000 亿，PE 20-60",
        "filters": {"market_cap_min": 500, "market_cap_max": 5000, "pe_min": 20, "pe_max": 60},
    },
    {
        "id": "large_cap",
        "name": "大盘蓝筹",
        "description": "市值 > 5000 亿，行业龙头",
        "filters": {"market_cap_min": 5000},
    },
]


def _apply_filter(quote: dict, filters: dict) -> bool:
    """检查单只股票是否满足全部筛选条件。"""
    if "change_pct_min" in filters and quote.get("change_pct", 0) < filters["change_pct_min"]:
        return False
    if "change_pct_max" in filters and quote.get("change_pct", 0) > filters["change_pct_max"]:
        return False
    if "turnover_min" in filters and quote.get("turnover", 0) < filters["turnover_min"]:
        return False
    if "turnover_max" in filters and quote.get("turnover", 0) > filters["turnover_max"]:
        return False
    pe = quote.get("pe", 0)
    if "pe_min" in filters and (pe <= 0 or pe < filters["pe_min"]):
        return False
    if "pe_max" in filters and pe > filters["pe_max"]:
        return False
    pb = quote.get("pb", 0)
    if "pb_min" in filters and (pb <= 0 or pb < filters["pb_min"]):
        return False
    if "pb_max" in filters and pb > filters["pb_max"]:
        return False
    mc = quote.get("market_cap", 0)
    if "market_cap_min" in filters and mc < filters["market_cap_min"]:
        return False
    if "market_cap_max" in filters and mc > filters["market_cap_max"]:
        return False
    if "industry" in filters and filters["industry"]:
        industry = quote.get("industry", "")
        if filters["industry"] not in industry:
            return False
    return True


async def run_scan(
    filters: dict | None = None,
    preset_id: str | None = None,
    sort_by: str = "market_cap",
    sort_desc: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    """执行选股扫描：获取股票池实时行情 → 筛选 → 排序。"""
    # 合并预设策略条件
    merged_filters: dict = {}
    if preset_id:
        preset = next((p for p in PRESETS if p["id"] == preset_id), None)
        if preset:
            merged_filters.update(preset.get("filters", {}))
    if filters:
        merged_filters.update(filters)

    # 批量获取行情（分批，每批最多 50 只避免 URL 过长）
    all_codes = [s["code"] for s in STOCK_POOL]
    quotes_map: dict[str, dict] = {}
    batch_size = 50
    for i in range(0, len(all_codes), batch_size):
        batch = all_codes[i:i + batch_size]
        result = await fetch_quotes(batch)
        quotes_map.update(result)

    # 合并行业信息并筛选
    results: list[dict] = []
    for stock in STOCK_POOL:
        code = stock["code"]
        quote = quotes_map.get(code)
        if not quote or quote.get("price", 0) <= 0:
            continue
        # 合并预设行业（腾讯行情不含行业字段）
        quote["industry"] = stock["industry"]
        quote["code"] = code
        quote["name"] = quote.get("name") or stock["name"]
        if _apply_filter(quote, merged_filters):
            results.append(quote)

    # 排序
    sort_key_map = {
        "market_cap": "market_cap",
        "change_pct": "change_pct",
        "turnover": "turnover",
        "pe": "pe",
        "pb": "pb",
        "price": "price",
    }
    key = sort_key_map.get(sort_by, "market_cap")
    results.sort(key=lambda x: x.get(key, 0), reverse=sort_desc)

    # 截断
    total = len(results)
    results = results[:limit]

    industries = sorted(set(s["industry"] for s in STOCK_POOL))

    return {
        "total": total,
        "returned": len(results),
        "filters": merged_filters,
        "sort_by": key,
        "sort_desc": sort_desc,
        "results": results,
        "industries": industries,
        "pool_size": len(STOCK_POOL),
        "data_source": "腾讯自选股公开行情接口",
        "disclaimer": "选股结果仅为条件筛选，不构成投资建议。须结合个股透视、334纪律与宏观矩阵交叉验证。",
    }
