"""异动雷达：ATR 基线 + 波动率/成交量突破 + 新闻反查。

不预测涨跌，不伪造资金流。只把价格异动和新闻事件放在同一条时间线上，
让用户自己判断因果关系和可持续性。
"""
import asyncio
from datetime import datetime, timedelta

from app.services.intelligence_data import get_intelligence_brief
from app.services.tencent_data import fetch_kline, fetch_minute_kline, fetch_quotes


def compute_atr(candles: list[dict], period: int = 14) -> float | None:
    """计算 ATR (Average True Range)。

    True Range = max(H-L, |H-prev_C|, |L-prev_C|)。
    需要至少 period+1 根 K 线（多一根用于前收）。
    """
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h = candles[i].get("high", 0)
        l = candles[i].get("low", 0)
        prev_c = candles[i - 1].get("close", 0)
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    # 取最后 period 根的简单移动平均
    atr = sum(trs[-period:]) / period
    return round(atr, 4) if atr > 0 else None


def compute_avg_volume(candles: list[dict], period: int = 10) -> float | None:
    """计算 N 日平均成交量。"""
    if len(candles) < period:
        return None
    vols = [c.get("volume", 0) for c in candles[-period:]]
    avg = sum(vols) / period
    return round(avg, 0) if avg > 0 else None


async def scan_stock(code: str, name: str = "") -> dict | None:
    """扫描单只标的的异动状态。

    返回 {code, name, price, change_pct, day_range, atr, range_ratio,
           volume, avg_volume, volume_ratio, anomaly_level, anomaly_type, news}。
    数据不可用时返回 None。
    """
    candles = await fetch_kline(code, "day", limit=25)
    if len(candles) < 15:
        return None

    atr = compute_atr(candles, period=14)
    avg_vol = compute_avg_volume(candles, period=10)
    if not atr or not avg_vol:
        return None

    quotes = await fetch_quotes([code])
    q = quotes.get(code)
    if not q or q.get("price", 0) == 0:
        return None

    day_high = q.get("high", 0)
    day_low = q.get("low", 0)
    day_range = day_high - day_low
    range_ratio = round(day_range / atr, 2) if atr > 0 else 0

    cur_vol = q.get("volume", 0)
    vol_ratio = round(cur_vol / avg_vol, 2) if avg_vol > 0 else 0

    # 异动分级
    level = "normal"
    types = []
    if range_ratio >= 2.0:
        level = "high"
        types.append("volatility_expansion")
    elif range_ratio >= 1.5:
        level = "medium"
        types.append("volatility_expansion")

    if vol_ratio >= 2.0:
        level = "high" if level != "normal" else "medium"
        types.append("volume_spike")
    elif vol_ratio >= 1.5 and level == "normal":
        level = "low"
        types.append("volume_spike")

    # 新闻反查：只在有异动时拉取
    news = []
    if level != "normal":
        try:
            brief = await get_intelligence_brief()
            for item in brief.get("news", [])[:10]:
                pub = item.get("published_at", "")
                title = item.get("title", "")
                # 简单关联：标题包含股票名称或代码
                if name and name in title:
                    news.append({"title": title, "published_at": pub, "source": item.get("source", "")})
                elif code in title:
                    news.append({"title": title, "published_at": pub, "source": item.get("source", "")})
        except Exception:
            pass

    return {
        "code": code,
        "name": name or q.get("name", ""),
        "price": q.get("price", 0),
        "change_pct": q.get("change_pct", 0),
        "day_high": day_high,
        "day_low": day_low,
        "day_range": round(day_range, 2),
        "atr": atr,
        "range_ratio": range_ratio,
        "volume": cur_vol,
        "avg_volume": avg_vol,
        "volume_ratio": vol_ratio,
        "anomaly_level": level,
        "anomaly_types": types,
        "news": news,
    }


async def scan_watchlist(watchlist: list[dict]) -> list[dict]:
    """批量扫描自选股异动，并发但限制为 5 个同时。"""
    if not watchlist:
        return []
    semaphore = asyncio.Semaphore(5)

    async def _scan(w: dict) -> dict | None:
        async with semaphore:
            return await scan_stock(w.get("code", ""), w.get("name", ""))

    results = await asyncio.gather(*[_scan(w) for w in watchlist])
    anomalies = [r for r in results if r and r["anomaly_level"] != "normal"]
    # 异动强度排序：high > medium > low
    order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda x: order.get(x["anomaly_level"], 9))
    return anomalies


async def pre_market_scan(watchlist: list[dict]) -> dict:
    """盘前扫描：隔夜新闻 × 自选股交叉筛选。

    返回 {overnight_news, flagged_stocks, updated_at}。
    flagged_stocks: 自选股中名字出现在隔夜新闻标题里的标的。
    """
    brief = await get_intelligence_brief()
    now = datetime.now()
    # 隔夜 = 过去 16 小时内的新闻（覆盖前一日收盘后到今日开盘前）
    cutoff = now - timedelta(hours=16)

    overnight = []
    for item in brief.get("news", [])[:30]:
        pub_str = item.get("published_at", "")
        # 简单解析：YYYY-MM-DD HH:MM 格式
        try:
            pub_dt = datetime.strptime(pub_str[:16], "%Y-%m-%d %H:%M")
            if pub_dt >= cutoff:
                overnight.append(item)
        except (ValueError, TypeError):
            overnight.append(item)

    # 交叉：自选股名称出现在新闻标题中
    flagged = []
    for w in watchlist:
        name = w.get("name", "")
        code = w.get("code", "")
        matched = []
        for news_item in overnight:
            title = news_item.get("title", "")
            if name and name in title:
                matched.append(news_item)
            elif code in title:
                matched.append(news_item)
        if matched:
            flagged.append({
                "code": code,
                "name": name,
                "matched_news": len(matched),
                "news": [{"title": n.get("title", ""), "published_at": n.get("published_at", "")} for n in matched[:5]],
            })

    return {
        "overnight_news_count": len(overnight),
        "overnight_news": [{"title": n.get("title", ""), "published_at": n.get("published_at", ""), "source": n.get("source", "")} for n in overnight[:15]],
        "flagged_stocks": flagged,
        "updated_at": now.isoformat(),
    }


def compute_intraday_spike(candles: list[dict]) -> dict | None:
    """检测分钟级价格/成交量异动。

    与日线 ATR 不同：盘中用过去 N 根分钟线的平均振幅和平均量做基线。
    当前根振幅或量 >= 2×基线时标记为盘中异动。
    """
    if len(candles) < 12:
        return None

    # 用前 N-2 根做基线，最后 2 根做检测
    baseline = candles[:-2]
    recent = candles[-2:]

    ranges = []
    volumes = []
    for c in baseline:
        h, l = c.get("high", 0), c.get("low", 0)
        if h > 0 and l > 0:
            ranges.append(h - l)
            volumes.append(c.get("volume", 0))

    if not ranges or sum(ranges) <= 0:
        return None
    avg_range = sum(ranges) / len(ranges)
    avg_vol = sum(volumes) / len(volumes) if volumes else 0

    flags = []
    max_range_ratio = 0
    max_vol_ratio = 0
    for c in recent:
        h, l = c.get("high", 0), c.get("low", 0)
        r = h - l
        rr = round(r / avg_range, 2) if avg_range > 0 else 0
        vr = round(c.get("volume", 0) / avg_vol, 2) if avg_vol > 0 else 0
        max_range_ratio = max(max_range_ratio, rr)
        max_vol_ratio = max(max_vol_ratio, vr)
        if rr >= 2.0:
            flags.append("intraday_range_spike")
        if vr >= 2.0:
            flags.append("intraday_volume_spike")

    if not flags:
        return None
    return {
        "spike_types": list(set(flags)),
        "range_ratio": max_range_ratio,
        "volume_ratio": max_vol_ratio,
        "last_time": recent[-1].get("datetime", ""),
    }


def summarize_intraday_flow(candles: list[dict]) -> dict:
    """提取分钟线中的量价方向代理，不把它命名为主力资金流。"""
    if not candles:
        return {
            "flow_direction": "unknown", "flow_direction_label": "数据不足",
            "max_volume_time": "", "max_range_time": "", "velocity_ratio": 0,
        }
    max_volume = max(candles, key=lambda item: item.get("volume", 0))
    max_range = max(
        candles,
        key=lambda item: item.get("high", 0) - item.get("low", 0),
    )
    signed_volume = sum(
        item.get("volume", 0) * (1 if item.get("close", 0) >= item.get("open", 0) else -1)
        for item in candles
    )
    total_volume = sum(item.get("volume", 0) for item in candles)
    if not total_volume:
        direction = "unknown"
    elif signed_volume > total_volume * 0.15:
        direction = "up"
    elif signed_volume < -total_volume * 0.15:
        direction = "down"
    else:
        direction = "mixed"
    labels = {"up": "上涨量能占优", "down": "下跌量能占优", "mixed": "多空混合", "unknown": "数据不足"}
    average_move = sum(abs(item.get("close", 0) - item.get("open", 0)) for item in candles) / len(candles)
    recent_move = abs(candles[-1].get("close", 0) - candles[-1].get("open", 0))
    return {
        "flow_direction": direction,
        "flow_direction_label": labels[direction],
        "max_volume_time": max_volume.get("datetime", ""),
        "max_volume": max_volume.get("volume", 0),
        "max_range_time": max_range.get("datetime", ""),
        "max_range": round(max_range.get("high", 0) - max_range.get("low", 0), 4),
        "velocity_ratio": round(recent_move / average_move, 2) if average_move else 0,
    }


async def intraday_scan(code: str, name: str = "") -> dict | None:
    """盘中异动扫描：分钟级 K 线检测 + 日线 ATR 交叉验证。"""
    intraday = await fetch_minute_kline(code, period="5m", limit=60)
    if not intraday:
        return None

    spike = compute_intraday_spike(intraday)
    if not spike:
        return {"code": code, "name": name, "intraday": False, "available": True}

    quotes = await fetch_quotes([code])
    q = quotes.get(code) or {}
    flow = summarize_intraday_flow(intraday)
    news = []
    try:
        brief = await get_intelligence_brief()
        for item in brief.get("news", [])[:20]:
            title = item.get("title", "")
            if (name and name in title) or code in title:
                news.append({
                    "title": title,
                    "published_at": item.get("published_at", ""),
                    "source": item.get("source", ""),
                })
    except Exception:
        news = []
    return {
        "code": code,
        "name": name or q.get("name", ""),
        "intraday": True,
        "available": True,
        "price": q.get("price", 0),
        "change_pct": q.get("change_pct", 0),
        "spike_types": spike["spike_types"],
        "range_ratio": spike["range_ratio"],
        "volume_ratio": spike["volume_ratio"],
        "last_time": spike["last_time"],
        **flow,
        "news": news[:5],
        "news_relation": "matched" if news else "unmatched",
    }
