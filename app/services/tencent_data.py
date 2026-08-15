"""腾讯自选股公开行情接口封装。

无需 AKShare / Node，本地与 Render 均可部署，作为行情与 K 线的首选数据源：
- 行情快照：qt.gtimg.cn（GBK 文本，~ 分隔）
- 前复权 K 线：web.ifzq.gtimg.cn（JSON）

字段索引遵循腾讯 v_ 行情接口约定（0 起）：
3 最新价 | 4 昨收 | 5 今开 | 6 成交量(手) | 30 时间 | 31 涨跌额 | 32 涨跌幅
33 最高 | 34 最低 | 38 换手率 | 39 市盈率TTM | 45 总市值(亿) | 46 市净率
"""
import codecs
import logging
import time

import httpx

from app.services.resilience import CircuitBreaker, run_with_retry

logger = logging.getLogger(__name__)

# ---- 内存缓存 ----
# 行情缓存：TTL 30 秒，避免短时间内对同一批股票的重复请求
_QUOTE_CACHE: dict[str, tuple[float, dict]] = {}
_QUOTE_CACHE_TTL = 30.0  # 秒


def _cache_get(key: str) -> dict | None:
    """读取缓存，过期返回 None。"""
    entry = _QUOTE_CACHE.get(key)
    if entry and (time.time() - entry[0]) < _QUOTE_CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: dict) -> None:
    _QUOTE_CACHE[key] = (time.time(), value)


def clear_quote_cache() -> None:
    """清空行情缓存（测试用）。"""
    _QUOTE_CACHE.clear()


def _decode_unicode_escapes(s: str) -> str:
    """腾讯 smartbox 返回的中文名是 \\u8d35\\u5dde 格式的 unicode 转义字符串，
    需要解码为实际中文字符。"""
    if "\\u" not in s:
        return s
    try:
        return codecs.decode(s, "unicode_escape")
    except Exception:
        return s

QUOTE_URL = "https://qt.gtimg.cn/q={symbols}"
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
TIMEOUT = 10.0

# 连接类错误值得重试；读/写超时（端点挂起）重试无益，交给熔断快速失败。
_RETRY_ON = (httpx.ConnectError, httpx.ConnectTimeout)
_QUOTE_BREAKER = CircuitBreaker()
_KLINE_BREAKER = CircuitBreaker()


async def _request(url: str, params: dict | None = None):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await client.get(url, params=params)


def to_tencent_symbol(code: str, is_index: bool = False) -> str:
    """6 位代码 -> 腾讯符号（sh/sz/bj）。

    is_index=True 时按指数规则映射：399xxx -> sz，其余（000xxx/880xxx
    等上证与中证系列）-> sh。避免 000001 被误判为深圳个股「平安银行」。
    """
    code = (code or "").strip().lower()
    for prefix in ("sh", "sz", "bj"):
        if code.startswith(prefix):
            code = code[2:]
            break
    code = code.split(".")[0]
    if not code.isdigit() or len(code) != 6:
        return ""
    if is_index:
        return f"sz{code}" if code.startswith("399") else f"sh{code}"
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("0", "3")):
        return f"sz{code}"
    return f"bj{code}"


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_quote_line(line: str) -> dict | None:
    """解析 qt.gtimg.cn 返回的一行行情。"""
    if "=" not in line:
        return None
    payload = line.split("=", 1)[1].strip().strip(';').strip('"').strip("'")
    parts = payload.split("~")
    if len(parts) < 48:
        return None
    try:
        return {
            "name": str(parts[1]),
            "code": str(parts[2]),
            "price": _f(parts[3]),
            "prev_close": _f(parts[4]),
            "open": _f(parts[5]),
            "volume": int(_f(parts[6])),
            "as_of": str(parts[30]),
            "change": _f(parts[31]),
            "change_pct": _f(parts[32]),
            "high": _f(parts[33]),
            "low": _f(parts[34]),
            "turnover": _f(parts[38]),
            "pe": _f(parts[39]),
            "market_cap": _f(parts[45]),
            "pb": _f(parts[46]),
        }
    except Exception:
        return None


async def fetch_quotes(codes: list[str], is_index: bool = False) -> dict[str, dict]:
    """批量获取行情快照，返回 {6位代码: {...}}；失败或无法识别时返回 {}。

    is_index=True 时按指数代码映射市场前缀（用于上证/深证/中证系列指数）。
    内置 30 秒内存缓存，减少对外部 API 的重复调用。
    """
    # 去重 + 排序，保证缓存 key 稳定
    codes = sorted(set(codes))
    cache_key = f"q:{','.join(codes)}:{is_index}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    symbols, mapping = [], {}
    for code in codes:
        symbol = to_tencent_symbol(code, is_index=is_index)
        if symbol:
            symbols.append(symbol)
            mapping[symbol] = code
    if not symbols:
        result = {}
        _cache_set(cache_key, result)
        return result
    try:
        resp = await run_with_retry(
            lambda: _request(QUOTE_URL.format(symbols=",".join(symbols))),
            breaker=_QUOTE_BREAKER,
            retry_on=_RETRY_ON,
        )
        text = resp.content.decode("gbk", errors="replace")
    except Exception as e:
        logger.warning("腾讯行情获取失败: %s", e)
        return {}

    result: dict[str, dict] = {}
    for line in text.split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        quote = parse_quote_line(line)
        if quote:
            result[mapping.get(quote["code"], quote["code"])] = quote
    _cache_set(cache_key, result)
    return result


async def fetch_kline(code: str, period: str = "day", limit: int = 120, is_index: bool = False) -> list[dict]:
    """获取前复权 K 线。period: day/week。返回 [{date,open,close,high,low,volume}]。

    is_index=True 时按指数代码映射市场前缀（用于指数 K 线）。
    """
    symbol = to_tencent_symbol(code, is_index=is_index)
    if not symbol:
        return []
    params = {"param": f"{symbol},{period},,,{limit},qfq"}
    try:
        resp = await run_with_retry(
            lambda: _request(KLINE_URL, params=params),
            breaker=_KLINE_BREAKER,
            retry_on=_RETRY_ON,
        )
        data = resp.json()
        node = data.get("data", {}).get(symbol, {}) or {}
        rows = node.get(f"qfq{period}") or node.get(period) or []
        candles = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 6:
                continue
            candles.append({
                "date": str(row[0]),
                "open": _f(row[1]),
                "close": _f(row[2]),
                "high": _f(row[3]),
                "low": _f(row[4]),
                "volume": int(_f(row[5])),
            })
        return candles
    except Exception as e:
        logger.warning("腾讯K线获取失败: %s", e)
        return []


_GLOBAL_INDEX_SYMBOLS: dict[str, dict] = {
    "usDJI":   {"name": "道琼斯",     "region": "美股"},
    "usIXIC":  {"name": "纳斯达克",   "region": "美股"},
    "usNDX":   {"name": "纳指100",    "region": "美股"},
    "usSPX":   {"name": "标普500",    "region": "美股"},
    "usVIX":   {"name": "VIX 波动率", "region": "美股"},
    "hkHSI":   {"name": "恒生指数",   "region": "港股"},
    "hkHSCEI": {"name": "国企指数",   "region": "港股"},
    "ukUKX":   {"name": "富时100",    "region": "欧洲"},
}


async def fetch_global_indices() -> list[dict]:
    """获取海外主要指数实时行情。

    返回 [{name, region, price, change_pct, change, as_of}]。
    腾讯覆盖美股+恒生+富时，日经/DAX/CAC 由 AKShare 兜底。
    """
    symbols = ",".join(_GLOBAL_INDEX_SYMBOLS.keys())
    try:
        resp = await run_with_retry(
            lambda: _request(QUOTE_URL.format(symbols=symbols)),
            breaker=_QUOTE_BREAKER,
            retry_on=_RETRY_ON,
        )
        text = resp.content.decode("gbk", errors="replace")
    except Exception as e:
        logger.warning("海外指数获取失败: %s", e)
        return []

    indices = []
    for line in text.split(";"):
        line = line.strip()
        if not line or "none_match" in line:
            continue
        sym = line.split("=")[0].lstrip("v_")
        if sym not in _GLOBAL_INDEX_SYMBOLS:
            continue
        quote = parse_quote_line(line)
        if not quote:
            continue
        meta = _GLOBAL_INDEX_SYMBOLS[sym]
        indices.append({
            "name": meta["name"],
            "region": meta["region"],
            "price": round(quote["price"], 2),
            "change_pct": round(quote["change_pct"], 2),
            "change": round(quote["change"], 2),
            "as_of": quote.get("as_of", ""),
        })
    # 补位：腾讯不支持的日经/DAX/CAC
    try:
        extra = await _fetch_indices_fallback()
        indices.extend(extra)
    except Exception:
        pass
    return indices


_NEED_AKSHARE_INDICES = {
    "N225": {"name": "日经225", "region": "日本"},
    "GDAXI": {"name": "德国DAX", "region": "欧洲"},
    "FCHI": {"name": "法国CAC40", "region": "欧洲"},
}


async def _fetch_indices_fallback() -> list[dict]:
    """AKShare 兜底：补全日经225/DAX/CAC40（腾讯不支持）。"""
    try:
        import akshare as ak
        df = ak.index_global_spot_em()
        if df is None or df.empty:
            return []
        results = []
        code_col = df.columns[0]
        for ak_code, meta in _NEED_AKSHARE_INDICES.items():
            row = df[df[code_col].astype(str).str.upper() == ak_code.upper()]
            if row.empty:
                continue
            r = row.iloc[0]
            try:
                row_dict = r.to_dict()
                price = float(row_dict.get("最新价", 0) or 0)
                change = float(row_dict.get("涨跌额", 0) or 0)
                change_pct = float(row_dict.get("涨跌幅", 0) or 0)
            except Exception:
                continue
            if price <= 0:
                continue
            results.append({
                "name": meta["name"],
                "region": meta["region"],
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "change": round(change, 2),
                "as_of": "",
            })
        if results:
            logger.info("AKShare 补位海外指数: %d 个", len(results))
        return results
    except Exception as e:
        logger.info("AKShare 海外指数兜底失败: %s", e)
        return []


SMARTBOX_URL = "https://smartbox.gtimg.cn/s3/"
_A_SHARE_MARKETS = ("sh", "sz", "bj")


async def smartbox_search(query: str, limit: int = 10) -> list[dict]:
    """腾讯自选股实时搜索（全市场，按相关度排序）。

    返回 [{code, name, symbol}]，仅保留 A 股（sh/sz/bj，类型 GP-A）；
    返回格式：v_hint="市场~代码~名称~拼音~类型^...^"，GBK 编码。
    """
    query = (query or "").strip()
    if not query:
        return []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(SMARTBOX_URL, params={"v": "2", "q": query, "t": "all"})
            text = resp.content.decode("gbk", errors="replace")
    except Exception as e:
        logger.warning("腾讯搜索失败: %s", e)
        return []

    start = text.find('="')
    if start < 0:
        return []
    start += 2
    end = text.rfind('"', start)
    if end <= start:
        return []
    payload = text[start:end]
    results: list[dict] = []
    for item in payload.split("^"):
        parts = item.split("~")
        if len(parts) < 5:
            continue
        market, code, name = parts[0], parts[1], parts[2]
        item_type = parts[4]
        # A 股类型：GP-A（主板/创业板）、GP-A-KCB（科创板）等均以 GP-A 开头
        if market not in _A_SHARE_MARKETS or not item_type.startswith("GP-A"):
            continue
        name = _decode_unicode_escapes(name)
        results.append({"code": code, "name": name, "symbol": f"{market}{code}"})
        if len(results) >= limit:
            break
    return results
