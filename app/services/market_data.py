"""ROX投资助手 — 市场数据服务

双轨策略：
1. 优先使用 AKShare 获取实时数据（Render 部署时生效）
2. AKShare 不可用时回退到 NeoData 拉取的真实数据快照（本地开发用）
"""
import logging
import os
from typing import Any

from app.services.tencent_data import fetch_kline, fetch_quotes, fetch_sina_quote, to_tencent_symbol

logger = logging.getLogger(__name__)

# 清除沙箱代理（本地开发时需要）
for _k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(_k, None)

# ============ 真实数据快照（NeoData 2026-07-29 拉取） ============

REAL_QUOTES = {
    # 白酒 (3)
    "600519": {"name": "贵州茅台", "industry": "白酒", "price": 1321.00, "change_pct": 0.08,
               "pe": 19.96, "pb": 7.09, "market_cap": 16513.58, "turnover": 0.50},
    "000858": {"name": "五粮液", "industry": "白酒", "price": 112.30, "change_pct": 0.45,
               "pe": 15.80, "pb": 4.21, "market_cap": 4360.0, "turnover": 0.42},
    "000568": {"name": "泸州老窖", "industry": "白酒", "price": 168.00, "change_pct": 0,
               "pe": 14.5, "pb": 5.20, "market_cap": 2470.0, "turnover": 0.55},
    # 银行 (4)
    "600036": {"name": "招商银行", "industry": "银行", "price": 35.42, "change_pct": 0.28,
               "pe": 6.85, "pb": 0.98, "market_cap": 8940.0, "turnover": 0.35},
    "601398": {"name": "工商银行", "industry": "银行", "price": 7.40, "change_pct": 0,
               "pe": 5.60, "pb": 0.62, "market_cap": 19500.0, "turnover": 0.10},
    "601939": {"name": "建设银行", "industry": "银行", "price": 8.82, "change_pct": 0,
               "pe": 5.40, "pb": 0.65, "market_cap": 15500.0, "turnover": 0.08},
    "000001": {"name": "平安银行", "industry": "银行", "price": 11.19, "change_pct": 0,
               "pe": 4.50, "pb": 0.52, "market_cap": 2170.0, "turnover": 0.25},
    # 保险 (3)
    "601318": {"name": "中国平安", "industry": "保险", "price": 56.40, "change_pct": 0.36,
               "pe": 7.90, "pb": 1.02, "market_cap": 10280.0, "turnover": 0.44},
    "601628": {"name": "中国人寿", "industry": "保险", "price": 38.60, "change_pct": 0,
               "pe": 22.0, "pb": 2.10, "market_cap": 10900.0, "turnover": 0.12},
    "601601": {"name": "中国太保", "industry": "保险", "price": 36.50, "change_pct": 0,
               "pe": 9.80, "pb": 1.15, "market_cap": 3510.0, "turnover": 0.18},
    # 证券 (1)
    "600030": {"name": "中信证券", "industry": "证券", "price": 26.80, "change_pct": 0,
               "pe": 15.10, "pb": 1.38, "market_cap": 3970.0, "turnover": 0.65},
    # 半导体 (4)
    "002371": {"name": "北方华创", "industry": "半导体", "price": 312.60, "change_pct": 2.14,
               "pe": 28.50, "pb": 6.12, "market_cap": 2265.0, "turnover": 0.85},
    "688981": {"name": "中芯国际", "industry": "半导体", "price": 86.52, "change_pct": 1.15,
               "pe": 98.20, "pb": 4.02, "market_cap": 6900.0, "turnover": 1.08},
    "002049": {"name": "紫光国微", "industry": "半导体", "price": 82.40, "change_pct": 0,
               "pe": 45.0, "pb": 7.80, "market_cap": 700.0, "turnover": 0.80},
    "603501": {"name": "韦尔股份", "industry": "半导体", "price": 128.60, "change_pct": 0,
               "pe": 32.0, "pb": 4.50, "market_cap": 1560.0, "turnover": 0.90},
    # 新能源/电池 (3)
    "300750": {"name": "宁德时代", "industry": "电池", "price": 231.21, "change_pct": 0.55,
               "pe": 22.10, "pb": 4.32, "market_cap": 10170.0, "turnover": 0.78},
    "601012": {"name": "隆基绿能", "industry": "新能源", "price": 16.73, "change_pct": -0.83,
               "pe": 24.80, "pb": 1.56, "market_cap": 1268.0, "turnover": 0.84},
    "300274": {"name": "阳光电源", "industry": "新能源", "price": 82.50, "change_pct": 0,
               "pe": 18.5, "pb": 4.30, "market_cap": 1710.0, "turnover": 0.90},
    # 医药 (3)
    "600276": {"name": "恒瑞医药", "industry": "医药", "price": 58.40, "change_pct": 0,
               "pe": 38.5, "pb": 5.20, "market_cap": 3720.0, "turnover": 0.55},
    "000538": {"name": "云南白药", "industry": "医药", "price": 55.60, "change_pct": 0,
               "pe": 18.0, "pb": 2.10, "market_cap": 1000.0, "turnover": 0.30},
    "300015": {"name": "爱尔眼科", "industry": "医药", "price": 14.50, "change_pct": 0,
               "pe": 50.0, "pb": 8.50, "market_cap": 1350.0, "turnover": 0.55},
    # 汽车 (3)
    "002594": {"name": "比亚迪", "industry": "乘用车", "price": 245.80, "change_pct": 1.84,
               "pe": 20.30, "pb": 4.15, "market_cap": 7150.0, "turnover": 0.68},
    "600104": {"name": "上汽集团", "industry": "乘用车", "price": 15.60, "change_pct": 0,
               "pe": 12.0, "pb": 0.80, "market_cap": 1820.0, "turnover": 0.20},
    "000625": {"name": "长安汽车", "industry": "乘用车", "price": 14.80, "change_pct": 0,
               "pe": 10.5, "pb": 1.95, "market_cap": 1470.0, "turnover": 0.50},
    # 家电 (2)
    "000651": {"name": "格力电器", "industry": "家电", "price": 40.60, "change_pct": 0,
               "pe": 8.20, "pb": 1.45, "market_cap": 2290.0, "turnover": 0.30},
    "000333": {"name": "美的集团", "industry": "家电", "price": 72.50, "change_pct": 0,
               "pe": 14.0, "pb": 3.10, "market_cap": 5540.0, "turnover": 0.40},
    # 消费 (1)
    "600887": {"name": "伊利股份", "industry": "食品", "price": 25.80, "change_pct": 0,
               "pe": 16.0, "pb": 3.50, "market_cap": 1640.0, "turnover": 0.35},
    # 电力 (2)
    "600900": {"name": "长江电力", "industry": "电力", "price": 29.18, "change_pct": 0.62,
               "pe": 22.40, "pb": 3.18, "market_cap": 7090.0, "turnover": 0.31},
    "601088": {"name": "中国神华", "industry": "煤炭", "price": 38.20, "change_pct": 0,
               "pe": 12.5, "pb": 1.75, "market_cap": 7590.0, "turnover": 0.15},
    # 石油 (1)
    "601857": {"name": "中国石油", "industry": "石油", "price": 8.40, "change_pct": 0,
               "pe": 10.5, "pb": 0.78, "market_cap": 15400.0, "turnover": 0.06},
    # 有色/稀土 (1)
    "000831": {"name": "中国稀土", "industry": "有色金属", "price": 32.50, "change_pct": 0,
               "pe": 45.0, "pb": 3.80, "market_cap": 480.0, "turnover": 1.50},
    # 钢铁 (1)
    "600019": {"name": "宝钢股份", "industry": "钢铁", "price": 6.80, "change_pct": 0,
               "pe": 10.5, "pb": 0.72, "market_cap": 1500.0, "turnover": 0.20},
    # 建筑 (1)
    "601668": {"name": "中国建筑", "industry": "建筑", "price": 5.60, "change_pct": 0,
               "pe": 4.50, "pb": 0.58, "market_cap": 2350.0, "turnover": 0.18},
    # 地产 (1)
    "000002": {"name": "万科A", "industry": "房地产", "price": 7.20, "change_pct": 0,
               "pe": 12.0, "pb": 0.42, "market_cap": 860.0, "turnover": 0.40},
    # 通信 (2)
    "300308": {"name": "中际旭创", "industry": "通信设备", "price": 156.80, "change_pct": 1.22,
               "pe": 35.60, "pb": 5.81, "market_cap": 1740.0, "turnover": 1.12},
    "600050": {"name": "中国联通", "industry": "通信", "price": 5.80, "change_pct": 0,
               "pe": 18.0, "pb": 0.95, "market_cap": 1840.0, "turnover": 0.15},
    # 计算机/AI (2)
    "002415": {"name": "海康威视", "industry": "计算机", "price": 31.06, "change_pct": -0.41,
               "pe": 18.10, "pb": 2.36, "market_cap": 2890.0, "turnover": 0.53},
    "002230": {"name": "科大讯飞", "industry": "计算机", "price": 78.50, "change_pct": 0,
               "pe": 65.0, "pb": 5.80, "market_cap": 1820.0, "turnover": 1.50},
    # 传媒 (1)
    "300413": {"name": "芒果超媒", "industry": "传媒", "price": 28.60, "change_pct": 0,
               "pe": 22.5, "pb": 2.20, "market_cap": 535.0, "turnover": 0.60},
    # 军工 (2)
    "600760": {"name": "中航沈飞", "industry": "军工", "price": 42.80, "change_pct": 0,
               "pe": 55.0, "pb": 5.20, "market_cap": 1180.0, "turnover": 0.40},
    "600893": {"name": "航发动力", "industry": "军工", "price": 45.20, "change_pct": 0,
               "pe": 60.0, "pb": 3.80, "market_cap": 1205.0, "turnover": 0.35},
    # 化工 (1)
    "600309": {"name": "万华化学", "industry": "化工", "price": 68.00, "change_pct": 0,
               "pe": 16.5, "pb": 3.20, "market_cap": 2140.0, "turnover": 0.30},
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
    """获取个股行情，并明确标注实时/快照状态。

    数据源优先级：腾讯 → 新浪 → AKShare → NeoData 快照。
    """
    code = normalize_stock_code(code)

    # 首选：腾讯自选股公开接口
    try:
        quotes = await fetch_quotes([code])
        if code in quotes:
            q = quotes[code]
            return {
                "code": code, "name": q["name"],
                "industry": REAL_QUOTES.get(code, {}).get("industry", ""),
                "price": q["price"], "change": q["change"], "change_pct": q["change_pct"],
                "pe": q["pe"], "pb": q["pb"],
                "market_cap": f"{q['market_cap']:.0f}亿" if q.get("market_cap") else "",
                "turnover": q["turnover"], "open": q["open"], "high": q["high"], "low": q["low"],
                "volume": q["volume"],
                "data_status": "realtime", "data_source": "腾讯自选股公开接口",
                "as_of": q["as_of"], "stale": False,
            }
    except Exception as e:
        logger.warning(f"腾讯行情回退: {e}")

    # 其次：新浪财经公开接口（价格/成交量，无估值字段）
    try:
        symbol = to_tencent_symbol(code)
        q = await fetch_sina_quote(code, symbol)
        if q:
            return {
                "code": code, "name": q["name"],
                "industry": REAL_QUOTES.get(code, {}).get("industry", ""),
                "price": q["price"], "change": q["change"], "change_pct": q["change_pct"],
                "pe": None, "pb": None, "market_cap": "", "turnover": None,
                "open": q["open"], "high": q["high"], "low": q["low"], "volume": q["volume"],
                "data_status": "realtime", "data_source": "新浪财经公开接口",
                "as_of": q["as_of"], "stale": False,
            }
    except Exception as e:
        logger.warning(f"新浪行情回退: {e}")

    # 其次：AKShare（带短超时，失败快速回退）
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

    return {
        "error": "未找到该股票或数据源暂不可用", "code": code,
        "data_status": "unavailable", "data_source": None, "as_of": None, "stale": True,
    }


async def get_kline(code: str, period: str = "daily", limit: int = 120) -> dict[str, Any]:
    """获取K线数据；失败时不生成模拟行情。

    数据源优先级：腾讯自选股公开接口 → AKShare。
    """
    code = normalize_stock_code(code)
    tencent_period = "day" if period == "daily" else "week"

    # 首选：腾讯自选股公开接口
    try:
        candles = await fetch_kline(code, tencent_period, limit)
        if candles:
            return {
                "code": code, "name": REAL_QUOTES.get(code, {}).get("name", code),
                "period": period, "candles": candles, "data_status": "realtime",
                "data_source": "腾讯自选股公开接口", "stale": False,
            }
    except Exception as e:
        logger.warning(f"腾讯K线回退: {e}")

    # 其次：AKShare
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
        "candles": [], "data_status": "unavailable", "data_source": None, "as_of": None, "stale": True,
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
        "data_status": "unavailable", "data_source": None, "as_of": None, "stale": True,
        "message": "资金流数据源暂不可用。",
    }


async def get_market_indices() -> list[dict]:
    """获取市场指数"""
    target_codes = {"000001": "上证指数", "399001": "深证成指", "399006": "创业板指", "000300": "沪深300"}
    try:
        quotes = await fetch_quotes(list(target_codes), is_index=True)
        live = []
        for code, name in target_codes.items():
            quote = quotes.get(code)
            if not quote or quote.get("price", 0) <= 0:
                continue
            live.append({
                "name": name,
                "code": f"{code}.{'SH' if not code.startswith('399') else 'SZ'}",
                "price": quote["price"],
                "change": quote["change"],
                "change_pct": quote["change_pct"],
                "data_status": "realtime",
                "data_source": "腾讯自选股公开指数接口",
                "as_of": quote.get("as_of", ""),
                "stale": False,
            })
        if len(live) == len(target_codes):
            return live
    except Exception as e:
        logger.warning("腾讯指数获取失败: %s", e)

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
                        "data_status": "realtime",
                        "data_source": "AKShare/东方财富公开接口", "as_of": "", "stale": False,
                    })
            if len(indices) >= 3:
                return indices
        except Exception as e:
            logger.warning(f"AKShare 指数获取失败: {e}")

    # 回退到真实数据快照
    return [{"code": idx["code"], "name": idx["name"], "price": idx["price"],
             "change": round(idx["price"] * idx["change_pct"] / 100, 2),
             "change_pct": idx["change_pct"],
             "data_status": "snapshot",
             "data_source": "NeoData 历史快照", "as_of": "2026-07-29", "stale": True} for idx in REAL_INDICES]


# ============ 全市场股票名录（搜索用） ============
# AKShare 可用时拉取沪深京全 A 股（约 5000+），缓存 24 小时；不可用时降级内置池。
import json as _json
import time as _time

from app.core.config import settings as _settings

UNIVERSE_CACHE_FILE = os.path.join(_settings.DATA_DIR, "stock_universe.json")
UNIVERSE_TTL_SECONDS = 24 * 3600
_universe_cache: list[dict] | None = None
_universe_loaded_at: float = 0.0


def _fetch_universe_eastmoney() -> list[dict]:
    """东方财富全市场 A 股名录（沪深京，约 5500 只）。逐页容错，中断时保留已拉取部分。"""
    import httpx as _httpx
    base = "https://push2.eastmoney.com/api/qt/clist/get"
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
    stocks: list[dict] = []
    pn, total = 1, 0
    while True:
        try:
            params = {
                "pn": pn, "pz": 500, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f12", "fs": fs, "fields": "f12,f14",
            }
            r = _httpx.get(base, params=params, timeout=12)
            data = (r.json() or {}).get("data") or {}
            diff = data.get("diff") or []
            total = int(data.get("total", 0) or 0)
        except Exception as e:
            logger.warning(f"东方财富名录第 {pn} 页失败（保留已拉取 {len(stocks)} 条）: {e}")
            break
        if not diff:
            break
        for item in diff:
            code = str(item.get("f12", "")).zfill(6)
            name = str(item.get("f14", ""))
            if code and name:
                stocks.append({"code": code, "name": name})
        if len(stocks) >= total or pn >= 20:
            break
        pn += 1
    return stocks


def load_stock_universe(refresh: bool = False) -> list[dict]:
    """沪深京全 A 股名录 [{code, name}]。优先内存 → 文件缓存 → 东方财富 → AKShare。

    - 东财 clist 接口在本地沙箱与 Render 均可用，作为名录主源
    - AKShare 作为备用源
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

    # 2) 东方财富全市场接口（首选）
    stocks = _fetch_universe_eastmoney()

    # 3) AKShare 备用
    if not stocks and AKSHARE_AVAILABLE:
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            stocks = [{"code": str(r["code"]).zfill(6), "name": str(r["name"])} for _, r in df.iterrows()]
        except Exception as e:
            logger.warning(f"AKShare 名录获取失败: {e}")

    if stocks:
        try:
            os.makedirs(_settings.DATA_DIR, exist_ok=True)
            with open(UNIVERSE_CACHE_FILE, "w", encoding="utf-8") as f:
                _json.dump({"ts": now, "stocks": stocks}, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"股票名录缓存写入失败: {e}")
        _universe_cache = stocks
        _universe_loaded_at = now

    return _universe_cache or []
