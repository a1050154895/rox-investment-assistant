"""异动雷达 ATR 计算的离线测试。"""
from app.services.anomaly_scanner import compute_atr, compute_avg_volume


def _candle(o, c, h, l, v=10000):
    return {"open": o, "close": c, "high": h, "low": l, "volume": v}


def test_atr_basic():
    """15 根 K 线应该能算出 14 周期 ATR。"""
    candles = [
        _candle(10, 11, 12, 9),
        _candle(11, 12, 13, 10),
        _candle(12, 11, 13, 10),
        _candle(11, 13, 14, 11),
        _candle(13, 14, 15, 12),
        _candle(14, 13, 15, 12),
        _candle(13, 15, 16, 13),
        _candle(15, 14, 16, 13),
        _candle(14, 16, 17, 14),
        _candle(16, 15, 17, 14),
        _candle(15, 17, 18, 15),
        _candle(17, 16, 18, 15),
        _candle(16, 18, 19, 16),
        _candle(18, 17, 19, 16),
        _candle(17, 19, 20, 17),
    ]
    atr = compute_atr(candles, period=14)
    assert atr is not None
    assert atr > 0
    # TR of first candle is H-L = 3, so ATR should be around 3
    assert 2.5 < atr < 3.5


def test_atr_insufficient_data():
    """不足 15 根时返回 None。"""
    candles = [_candle(10, 11, 12, 9) for _ in range(10)]
    assert compute_atr(candles, period=14) is None


def test_atr_uses_true_range():
    """ATR 应考虑跳空：TR = max(H-L, |H-prev_C|, |L-prev_C|)。"""
    # Candle 1: close=10, Candle 2: open=15, high=16, low=14, close=15
    # TR = max(16-14=2, |16-10|=6, |14-10|=4) = 6
    candles = [
        _candle(10, 10, 11, 9),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
        _candle(15, 15, 16, 14),
    ]
    atr = compute_atr(candles, period=14)
    assert atr is not None
    # Second candle has a gap up (TR=6), rest are TR=2.
    # ATR = (6 + 2*13) / 14 = 2.29 — gap lifts it above 2.0.
    assert atr > 2.0


def test_avg_volume():
    candles = [_candle(10, 11, 12, 9, v=10000) for _ in range(12)]
    avg = compute_avg_volume(candles, period=10)
    assert avg == 10000.0


def test_avg_volume_insufficient():
    candles = [_candle(10, 11, 12, 9, v=10000) for _ in range(5)]
    assert compute_avg_volume(candles, period=10) is None


def test_scan_stock_no_data():
    """离线环境下（K线为空）应返回 None。"""
    import asyncio
    from app.services.anomaly_scanner import scan_stock
    result = asyncio.run(scan_stock("600519", "贵州茅台"))
    assert result is None


def test_scan_watchlist_empty():
    """空自选应返回空列表。"""
    import asyncio
    from app.services.anomaly_scanner import scan_watchlist
    result = asyncio.run(scan_watchlist([]))
    assert result == []
