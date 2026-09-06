"""更新公告数据层测试：公告版本与应用版本强制同步，防止发版漏写公告。"""
from app.main import app
from app.services import changelog as changelog_data
from app.services.changelog import get_changelog


class TestChangelog:
    def test_latest_version_matches_app_version(self):
        """最新公告条目的版本号必须与应用版本一致（发版漏写公告时此测试失败）。"""
        assert changelog_data.CHANGELOG, "公告列表不能为空"
        assert changelog_data.CHANGELOG[0]["version"] == app.version

    def test_changelog_entries_well_formed(self):
        data = get_changelog()
        assert data["latest_version"] == changelog_data.CHANGELOG[0]["version"]
        for entry in data["entries"]:
            assert entry["version"] and entry["date"] and entry["title"]
            assert entry["items"] and all(isinstance(i, str) and i for i in entry["items"])

    def test_intro_covers_positioning_and_risk(self):
        intro = get_changelog()["intro"]
        assert intro["name"] and intro["tagline"] and intro["positioning"]
        assert len(intro["core_objects"]) >= 4
        assert "不构成" in intro["risk"]

    def test_changelog_api_public(self, client):
        resp = client.get("/api/changelog")
        assert resp.status_code == 200
        data = resp.json()
        assert data["latest_version"] == app.version
        assert "entries" in data and "intro" in data
