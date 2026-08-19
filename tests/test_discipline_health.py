"""334 纪律体检（真实持仓 + 周期阶段）测试。"""
from app.services.discipline_engine import build_health_report


def _profile() -> dict:
    return {
        "core_pct": 30, "satellite_pct": 30, "cash_pct": 40,
        "max_total_position_pct": 60, "single_trade_risk_pct": 1,
        "stop_loss_pct": 8, "single_position_limit_pct": 15,
        "sector_limit_pct": 30, "current_sector_exposure_pct": 0,
        "planned_position_pct": 0, "monthly_trades": 0,
        "monthly_trade_limit": 2, "operating_rules": "",
    }


def _portfolio() -> dict:
    return {"count": 0, "total_cost": 0.0, "total_market": 0.0, "positions": []}


def test_health_report_unevaluated_cycle():
    report = build_health_report(_profile(), _portfolio(), {"stage_name": "未评估", "stage_detail": "缺数据", "evidence": ""})
    assert report["cycle"]["stage"] == "未评估"
    assert report["cycle"]["allow_trial"] is False
    assert "未评估" in report["guidance"]


def test_health_report_concentration_cycle():
    report = build_health_report(_profile(), _portfolio(), {"stage_name": "集中", "stage_detail": "", "evidence": ""})
    assert report["cycle"]["posture"] == "布局龙头，试仓进入"
    assert report["cycle"]["allow_trial"] is True


def test_health_report_merges_all_sections():
    report = build_health_report(_profile(), _portfolio(), {"stage_name": "积累", "stage_detail": "", "evidence": ""})
    for key in ("profile", "portfolio", "cycle", "assessment", "guidance", "disclaimer"):
        assert key in report


class TestAssessmentEndpoint:
    def test_requires_auth(self, client):
        assert client.get("/api/discipline/assessment").status_code == 401

    def test_returns_health_report(self, client, auth_headers):
        resp = client.get("/api/discipline/assessment", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ("profile", "portfolio", "cycle", "assessment", "guidance", "disclaimer"):
            assert key in data
        assert data["portfolio"]["count"] == 0
