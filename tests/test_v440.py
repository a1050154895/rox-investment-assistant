"""v4.40 事件持续性与宏观口径校验测试。"""
import json

from app.models import AnomalyEvent
from app.services.anomaly_scanner import classify_event_status
from app.services.macro_data import _period_bucket, _real_rate_proxy


def test_event_status_progresses_by_observation_and_date():
    first = [{"observed_at": "2026-08-28T10:00:00"}]
    same_day = first + [{"observed_at": "2026-08-28T10:05:00"}]
    persistent = same_day + [{"observed_at": "2026-08-28T10:15:00"}]
    next_day = persistent + [{"observed_at": "2026-08-29T09:35:00"}]
    assert classify_event_status(first) == "detected"
    assert classify_event_status(same_day) == "short_continuation"
    assert classify_event_status(persistent) == "intraday_persistent"
    assert classify_event_status(next_day) == "next_day_review"


def test_real_rate_proxy_refuses_mixed_periods():
    assert _period_bucket("2026年06月") == "2026Q2"
    assert _period_bucket("2026年第2季度") == "2026Q2"
    base = {
        "status": "available", "value": 1.0,
    }
    indicators = [
        {**base, "key": "lpr_1y", "period": "2026年06月"},
        {**base, "key": "cpi_yoy", "period": "2026年06月"},
        {**base, "key": "m2_yoy", "period": "2026年03月"},
        {**base, "key": "gdp_yoy", "period": "2026年第2季度"},
    ]
    result = _real_rate_proxy(indicators)
    assert result["status"] == "period_mismatch"
    assert result["value"] is None


def test_event_is_included_in_backup(client, auth_headers, dbsession):
    user_id = dbsession.query(AnomalyEvent).count()
    assert user_id == 0
    from app.models import User
    user = dbsession.query(User).first()
    event = AnomalyEvent(
        user_id=user.id, code="600519", name="贵州茅台", status="detected",
        snapshots_json=json.dumps([{ "observed_at": "2026-08-28T10:00:00" }]),
    )
    dbsession.add(event)
    dbsession.commit()
    backup = client.get("/api/export/backup", headers=auth_headers)
    assert backup.status_code == 200
    assert len(backup.json()["anomaly_events"]) == 1
