"""ROX投资助手 — 市场数据服务

双轨策略：
1. 优先使用 AKShare 获取实时数据（Render 部署时生效）
2. AKShare 不可用时回退到 NeoData 拉取的真实数据快照（本地开发用）
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# 清除沙箱代理（本地开发时需要）
for _k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(_k, None)

# ============ 真实数据快照（NeoData 2026-07-29 拉取） ============

REAL_QUOTES = {
    "600519": {"name": "贵州茅台", "industry": "白酒", "price": 1321.00, "change_pct": 0.08,
               "pe": 19.96, "pb": 7.09, "market_cap": 16513.58, "turnover": 0.50,
               "open": 1333.83, "high": 1343.48, "low": 1312.06, "prev_close": 1320.00,
               "volume": 62330, "amount": 828240.00, "dividend_yield": 3.94},
    "300750": {"name": "宁德时代", "industry": "电池", "price": 231.21, "change_pct": 0.55,
               "pe": 22.10, "pb": 4.32, "market_cap": 10170.0, "turnover": 0.78,
               "open": 230.00, "high": 234.50, "low": 228.80, "prev_close": 229.95,
               "volume": 185000, "amount": 42800.0, "dividend_yield": 0.32},
    "300308": {"name": "中际旭创", "industry": "通信设备", "price": 156.80, "change_pct": 1.22,
               "pe": 35.60, "pb": 5.81, "market_cap": 1740.0, "turnover": 1.12,
               "open": 155.00, "high": 158.90, "low": 154.20, "prev_close": 154.91,
               "volume": 110994, "amount": 17400.0, "dividend_yield": 0.28},
    "600036": {"name": "招商银行", "industry": "银行", "price": 35.42, "change_pct": 0.28,
               "pe": 6.85, "pb": 0.98, "market_cap": 8940.0, "turnover": 0.35,
               "open": 35.30, "high": 35.68, "low": 35.12, "prev_close": 35.32,
               "volume": 725110, "amount": 25680.0, "dividend_yield": 5.82},
    "002371": {"name": "北方华创", "industry": "半导体", "price": 312.60, "change_pct": 2.14,
               "pe": 28.50, "pb": 6.12, "market_cap": 2265.0, "turnover": 0.85,
               "open": 306.00, "high": 315.80, "low": 305.50, "prev_close": 306.05,
               "volume": 72511, "amount": 22650.0, "dividend_yield": 0.15},
    "000858": {"name": "五粮液", "industry": "白酒", "price": 112.30, "change_pct": 0.45,
               "pe": 15.80, "pb": 4.21, "market_cap": 4360.0, "turnover": 0.42,
               "open": 112.00, "high": 113.50, "low": 111.20, "prev_close": 111.80,
               "volume": 388151, "amount": 43500.0, "dividend_yield": 4.02},
    "002594": {"name": "比亚迪", "industry": "乘用车", "price": 245.80, "change_pct": 1.84,
               "pe": 20.30, "pb": 4.15, "market_cap": 7150.0, "turnover": 0.68,
               "open": 242.00, "high": 248.50, "low": 241.30, "prev_close": 241.35,
               "volume": 291000, "amount": 71500.0, "dividend_yield": 0.85},
    "601318": {"name": "中国平安", "industry": "保险", "price": 56.40, "change_pct": 0.36,
               "pe": 7.90, "pb": 1.02, "market_cap": 10280.0, "turnover": 0.44,
               "open": 56.10, "high": 56.80, "low": 55.90, "prev_close": 56.20,
               "volume": 514000, "amount": 28980.0, "dividend_yield": 4.70},
    "600900": {"name": "长江电力", "industry": "电力", "price": 29.18, "change_pct": 0.62,
               "pe": 22.40, "pb": 3.18, "market_cap": 7090.0, "turnover": 0.31,
               "open": 29.00, "high": 29.35, "low": 28.94, "prev_close": 29.00,
               "volume": 356000, "amount": 10390.0, "dividend_yield": 3.45},
    "688981": {"name": "中芯国际", "industry": "半导体", "price": 86.52, "change_pct": 1.15,
               "pe": 98.20, "pb": 4.02, "market_cap": 6900.0, "turnover": 1.08,
               "open": 85.48, "high": 87.20, "low": 85.10, "prev_close": 85.54,
               "volume": 267000, "amount": 23100.0, "dividend_yield": 0.0},
    "002415": {"name": "海康威视", "industry": "计算机", "price": 31.06, "change_pct": -0.41,
               "pe": 18.10, "pb": 2.36, "market_cap": 2890.0, "turnover": 0.53,
               "open": 31.25, "high": 31.38, "low": 30.92, "prev_close": 31.19,
               "volume": 442000, "amount": 13740.0, "dividend_yield": 2.95},
    "601012": {"name": "隆基绿能", "industry": "新能源", "price": 16.73, "change_pct": -0.83,
               "pe": 24.80, "pb": 1.56, "market_cap": 1268.0, "turnover": 0.84,
               "open": 16.90, "high": 16.95, "low": 16.62, "prev_close": 16.87,
               "volume": 726000, "amount": 12150.0, "dividend_yield": 0.65},
}

REAL_INDICES = [
    {"name": "上证指数", "code": "000001.SH", "price": 3828.47, "change_pct": 0.40},
    {"name": "深证成指", "code": "399001.SZ", "price": 13658.44, "change_pct": 1.10},
    {"name": "创业板指", "code": "399006.SZ", "price": 2156.33, "change_pct": 0.41},
    {"name": "沪深300", "code": "000300.SH", "price": 3842.16, "change_pct": 0.15},
]

REAL_FUND_FLOW = {
    "600519": {"main_inflow": 5.75, "main_in_pct": 32, "main_out_pct": 29,
               "retail_in_pct": 18, "retail_out_pct": 21},
}


def _try_akshare():
    """检查 AKShare 是否可用（含网络连通性检测）"""
    try:
        import akshare as ak
        if ak is None:
            return False
        # 快速连通性检测：尝试获取一个指数（3秒超时）
        import requests
        session = requests.Session()
        session.trust_env = False  # 忽略代理
        try:
            r = session.get(
                "https://push2.eastmoney.com/api/qt/stock/get",
                params={"secid": "1.000001", "fields": "f43"},
                timeout=3
            )
            return r.status_code == 200
        except Exception:
            return False
    except Exception:
        return False


AKSHARE_AVAILABLE = _try_akshare()
if AKSHARE_AVAILABLE:
    logger.info("AKShare 可用，将使用实时数据")
else:
    logger.info("AKShare 不可用，使用 NeoData 真实数据快照")


def normalize_stock_code(code: str) -> str:
    """标准化 A 股代码，避免 str.lstrip 对字符集合的误删行为。"""
    normalized = code.strip().lower()
    if normalized.startswith(("sh", "sz", "bj")):
        normalized = normalized[2:]
    return normalized.split(".")[0]


async def get_stock_quote(code: str) -> dict[str, Any]:
    """获取个股行情，并明确标注实时/快照状态。"""
    code = normalize_stock_code(code)

    # 尝试 AKShare（带短超时，失败快速回退）
    if AKSHARE_AVAILABLE:
        try:
            import akshare as ak
            import requests
            # monkey-patch requests session to bypass proxy and set timeout
            _orig_get = requests.get
            _orig_session = requests.Session
            class _NoProxySession(requests.Session):
                def __init__(self, *a, **kw):
                    super().__init__(*a, **kw)
                    self.trust_env = False
            requests.Session = _NoProxySession
            try:
                df = ak.stock_zh_a_spot_em()
            finally:
                requests.get = _orig_get
                requests.Session = _orig_session
            row = df[df['代码'] == code]
            if not row.empty:
                r = row.iloc[0]
                return {
                    "code": code,
                    "name": str(r.get('名称', '')),
                    "industry": "",
                    "price": float(r.get('最新价', 0) or 0),
                    "change": float(r.get('涨跌额', 0) or 0),
                    "change_pct": float(r.get('涨跌幅', 0) or 0),
                    "pe": float(r.get('市盈率-动态', 0) or 0),
                    "pb": float(r.get('市净率', 0) or 0),
                    "market_cap": f"{float(r.get('总市值', 0) or 0) / 1e8:.0f}亿",
                    "turnover": float(r.get('换手率', 0) or 0),
                    "open": float(r.get('今开', 0) or 0),
                    "high": float(r.get('最高', 0) or 0),
                    "low": float(r.get('最低', 0) or 0),
                    "volume": int(r.get('成交量', 0) or 0),
                    "data_status": "realtime", "data_source": "AKShare/东方财富公开接口",
                    "as_of": str(r.get('更新时间', '') or ''), "stale": False,
                }
        except Exception as e:
            logger.warning(f"AKShare 行情获取失败: {e}")

    # 回退到真实数据快照
    if code in REAL_QUOTES:
        q = REAL_QUOTES[code]
        return {
            "code": code, "name": q["name"], "industry": q["industry"],
            "price": q["price"], "change": round(q["price"] - q["prev_close"], 2),
            "change_pct": q["change_pct"], "pe": q["pe"], "pb": q["pb"],
            "market_cap": f"{q['market_cap']:.0f}亿", "turnover": q["turnover"],
            "open": q["open"], "high": q["high"], "low": q["low"],
            "data_status": "snapshot", "data_source": "NeoData 历史快照",
            "as_of": "2026-07-29", "stale": True,
        }

    return {"error": "未找到该股票或数据源暂不可用", "code": code, "data_status": "unavailable", "stale": True}


async def get_kline(code: str, period: str = "daily", limit: int = 120) -> dict[str, Any]:
    """获取K线数据；失败时不生成模拟行情。"""
    code = normalize_stock_code(code)
    ak_period = "daily" if period == "daily" else "weekly"

    # 尝试 AKShare
    if AKSHARE_AVAILABLE:
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            end = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=limit * 2)).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(symbol=code, period=ak_period, start_date=start, end_date=end, adjust='qfq')
            if not df.empty:
                candles = []
                for _, r in df.iterrows():
                    candles.append({
                        "date": str(r['日期']),
                        "open": float(r['开盘']),
                        "close": float(r['收盘']),
                        "high": float(r['最高']),
                        "low": float(r['最低']),
                        "volume": int(r['成交量']),
                    })
                return {"code": code, "name": REAL_QUOTES.get(code, {}).get("name", code),
                        "period": period, "candles": candles[-limit:], "data_status": "realtime",
                        "data_source": "AKShare/东方财富公开接口", "stale": False}
        except Exception as e:
            logger.warning(f"AKShare K线获取失败: {e}")

    return {
        "code": code, "name": REAL_QUOTES.get(code, {}).get("name", code), "period": period,
        "candles": [], "data_status": "unavailable", "data_source": None, "stale": True,
        "message": "K线数据源暂不可用，系统不会生成模拟行情。",
    }


async def get_fund_flow(code: str) -> dict[str, Any]:
    """获取资金流向；失败时仅返回已登记快照。"""
    code = normalize_stock_code(code)

    # 尝试 AKShare
    if AKSHARE_AVAILABLE:
        try:
            import akshare as ak
            market = 'sh' if code.startswith('6') else 'sz'
            df = ak.stock_individual_fund_flow(stock=code, market=market)
            if not df.empty:
                latest = df.iloc[-1]
                main_inflow = float(latest.get('主力净流入-净额', 0) or 0) / 1e8
                trend_data = []
                for _, r in df.tail(10).iterrows():
                    trend_data.append(round(float(r.get('主力净流入-净额', 0) or 0) / 1e8, 2))
                return {
                    "main_inflow": round(main_inflow, 2), "trend": trend_data,
                    "north_flow": None, "sector_comparison": None,
                    "data_status": "realtime", "data_source": "AKShare/东方财富公开接口", "stale": False,
                }
        except Exception as e:
            logger.warning(f"AKShare 资金流获取失败: {e}")

    if code in REAL_FUND_FLOW:
        ff = REAL_FUND_FLOW[code]
        return {
            "main_inflow": ff["main_inflow"], "trend": [],
            "north_flow": None, "sector_comparison": None,
            "data_status": "snapshot", "data_source": "NeoData 历史快照",
            "as_of": "2026-07-29", "stale": True,
        }
    return {
        "main_inflow": None, "trend": [], "north_flow": None, "sector_comparison": None,
        "data_status": "unavailable", "data_source": None, "stale": True,
        "message": "资金流数据源暂不可用。",
    }


async def get_market_indices() -> list[dict]:
    """获取市场指数"""
    # 尝试 AKShare
    if AKSHARE_AVAILABLE:
        try:
            import akshare as ak
            df = ak.stock_zh_index_spot_em()
            indices = []
            target_codes = {"000001": "上证指数", "399001": "深证成指", "399006": "创业板指", "000300": "沪深300"}
            for _, r in df.iterrows():
                code = str(r.get('代码', ''))
                if code in target_codes:
                    indices.append({
                        "name": target_codes[code],
                        "code": f"{code}.{'SH' if code.startswith('0') else 'SZ'}",
                        "price": float(r.get('最新价', 0) or 0),
                        "change": float(r.get('涨跌额', 0) or 0),
                        "change_pct": float(r.get('涨跌幅', 0) or 0),
                    })
            if len(indices) >= 3:
                return indices
        except Exception as e:
            logger.warning(f"AKShare 指数获取失败: {e}")

    # 回退到真实数据快照
    return [{"code": idx["code"], "name": idx["name"], "price": idx["price"],
             "change": round(idx["price"] * idx["change_pct"] / 100, 2),
             "change_pct": idx["change_pct"]} for idx in REAL_INDICES]


# ============ 全市场股票名录（搜索用） ============
# AKShare 可用时拉取沪深京全 A 股（约 5000+），缓存 24 小时；不可用时降级内置池。
import json as _json
import time as _time

from app.core.config import settings as _settings

UNIVERSE_CACHE_FILE = os.path.join(_settings.DATA_DIR, "stock_universe.json")
UNIVERSE_TTL_SECONDS = 24 * 3600
_universe_cache: list[dict] | None = None
_universe_loaded_at: float = 0.0


def load_stock_universe(refresh: bool = False) -> list[dict]:
    """沪深京全 A 股名录 [{code, name}]。优先内存 → 文件缓存 → AKShare 拉取。

    - AKShare 可用：拉取 `stock_info_a_code_name()` 并写入 data/stock_universe.json
    - AKShare 不可用：读取已有缓存文件（本地开发可预置）
    - 均不可用：返回 []（搜索接口将降级到内置 REAL_QUOTES 池）
    """
    global _universe_cache, _universe_loaded_at
    now = _time.time()
    if not refresh and _universe_cache is not None and now - _universe_loaded_at < UNIVERSE_TTL_SECONDS:
        return _universe_cache

    # 1) 文件缓存
    if not refresh and os.path.exists(UNIVERSE_CACHE_FILE):
        try:
            with open(UNIVERSE_CACHE_FILE, "r", encoding="utf-8") as f:
                payload = _json.load(f)
            if isinstance(payload, dict) and isinstance(payload.get("stocks"), list):
                if now - float(payload.get("ts", 0)) < UNIVERSE_TTL_SECONDS:
                    _universe_cache = payload["stocks"]
                    _universe_loaded_at = now
                    return _universe_cache
        except Exception as e:
            logger.warning(f"股票名录缓存读取失败: {e}")

    # 2) AKShare 拉取（Render 生产环境）
    if AKSHARE_AVAILABLE:
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            stocks = [{"code": str(r["code"]).zfill(6), "name": str(r["name"])} for _, r in df.iterrows()]
            try:
                os.makedirs(_settings.DATA_DIR, exist_ok=True)
                with open(UNIVERSE_CACHE_FILE, "w", encoding="utf-8") as f:
                    _json.dump({"ts": now, "stocks": stocks}, f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"股票名录缓存写入失败: {e}")
            _universe_cache = stocks
            _universe_loaded_at = now
            return stocks
        except Exception as e:
            logger.warning(f"全市场股票名录获取失败: {e}")

    return _universe_cache or []
