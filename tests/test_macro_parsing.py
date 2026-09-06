"""宏观指标解析测试：对接口返回顺序不做假设，永远取观察期最新的有效行。"""
import pandas as pd

from app.services.macro_data import IndicatorSpec, _growth_score, parse_indicator_frame


def _spec() -> IndicatorSpec:
    return IndicatorSpec(
        key="m2_yoy", label="M2 同比", function_name="macro_china_money_supply",
        value_columns=("M2同比增长",), date_columns=("月份",),
        publisher="中国人民银行", group="fiscal_credit", scorer=_growth_score,
    )


def test_ascending_frame_picks_latest():
    frame = pd.DataFrame([
        {"月份": "2026年01月", "M2同比增长": 8.0},
        {"月份": "2026年06月", "M2同比增长": 8.5},
        {"月份": "2026年07月", "M2同比增长": 9.0},
    ])
    result = parse_indicator_frame(frame, _spec())
    assert result["period"] == "2026年07月"
    assert result["value"] == 9.0
    assert result["status"] == "available"


def test_descending_frame_picks_same_latest():
    """接口若按新→旧排序，倒序遍历绝不能取到最老的一行（历史 bug）。"""
    frame = pd.DataFrame([
        {"月份": "2026年07月", "M2同比增长": 9.0},
        {"月份": "2026年06月", "M2同比增长": 8.5},
        {"月份": "2026年01月", "M2同比增长": 8.0},
    ])
    result = parse_indicator_frame(frame, _spec())
    assert result["period"] == "2026年07月"
    assert result["value"] == 9.0


def test_old_year_rows_filtered():
    frame = pd.DataFrame([
        {"月份": "2024年12月", "M2同比增长": 7.0},
        {"月份": "2026年07月", "M2同比增长": 9.0},
    ])
    result = parse_indicator_frame(frame, _spec())
    assert result["period"] == "2026年07月"


def test_unparseable_date_row_loses_to_dated_row():
    frame = pd.DataFrame([
        {"月份": "未知", "M2同比增长": 5.0},
        {"月份": "2026年07月", "M2同比增长": 9.0},
    ])
    result = parse_indicator_frame(frame, _spec())
    assert result["period"] == "2026年07月"
