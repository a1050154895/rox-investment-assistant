"""成交额集中度风险温度计（借鉴 Serenity/猫哥的集中度概念，诚实实现）。

口径：把全市场股票按当日成交额从高到低排序，前 5% 的股票合计成交额
占全市场的比例。值越高 = 资金越扎堆 = 一致预期越强，泡沫风险越大。

诚实边界：
- 只计算"当日"值（基于 AKShare/东财全市场快照），历史由本系统逐日
  快照自建（首次使用时历史很短，会如实说明）；
- 外部参考线（如"36个月新高45.86%"）来自第三方文章，未经本系统验证，
  仅作为背景注明，不作为信号。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import MarketConcentration

logger = logging.getLogger(__name__)


def compute_concentration(amounts: list[float]) -> dict[str, Any] | None:
    """纯计算：给定全市场成交额列表（元），返回集中度指标。"""
    values = sorted((a for a in amounts if a and a > 0), reverse=True)
    n = len(values)
    if n < 100:
        return None
    total = sum(values)

    def share(ratio: float) -> float:
        k = max(1, int(n * ratio))
        return round(sum(values[:k]) / total * 100, 2)

    return {
        "top5_pct": share(0.05),
        "top10_pct": share(0.10),
        "total_amount_yi": round(total / 1e8, 1),
        "stock_count": n,
    }


async def get_concentration(db: Session) -> dict[str, Any]:
    """获取当日集中度并落库快照；同时返回自建历史。"""
    status = "unavailable"
    metrics = None
    try:
        from app.services.akshare_gate import gated_call
        import akshare as ak

        def _fetch():
            import requests

            class _NoProxySession(requests.Session):
                def __init__(self, *a, **kw):
                    super().__init__(*a, **kw)
                    self.trust_env = False

            _orig = requests.Session
            requests.Session = _NoProxySession
            try:
                return ak.stock_zh_a_spot_em()
            finally:
                requests.Session = _orig

        df = await gated_call(_fetch)
        col = None
        for name in ("成交额", "成交额(元)"):
            if name in df.columns:
                col = name
                break
        if col is not None:
            metrics = compute_concentration([float(v) for v in df[col].tolist()])
            if metrics:
                status = "realtime"
    except Exception as exc:  # noqa: BLE001 — 数据不可用时诚实降级
        logger.info("集中度数据不可用: %s", exc)

    today = datetime.now().strftime("%Y-%m-%d")
    if metrics and status == "realtime":
        row = db.query(MarketConcentration).filter(MarketConcentration.date == today).first()
        if not row:
            db.add(MarketConcentration(date=today, **metrics))
            db.commit()

    history = (
        db.query(MarketConcentration)
        .order_by(MarketConcentration.date.desc())
        .limit(120)
        .all()
    )
    history_items = [
        {"date": h.date, "top5_pct": h.top5_pct, "top10_pct": h.top10_pct}
        for h in reversed(history)
    ]
    return {
        "data_status": status,
        **(metrics or {}),
        "history": history_items,
        "history_days": len(history_items),
        "method": "前5%股票成交额占全市场比例；历史为本系统逐日快照自建",
        "external_reference": "第三方研究曾以前5%集中度>43%作为36个月90%置信区间上界（未经本系统验证，仅供参考）",
        "as_of": today,
        "message": None if metrics else "全市场成交额数据暂不可用，不生成估计值",
    }
