"""快速速记 API 的离线测试。"""


def test_create_and_list_note(client, auth_headers):
    resp = client.post("/api/notes/", json={"content": "测试速记内容"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "测试速记内容"
    assert data["id"] > 0

    resp = client.get("/api/notes/", headers=auth_headers)
    assert resp.status_code == 200
    notes = resp.json()
    assert len(notes) == 1
    assert notes[0]["content"] == "测试速记内容"


def test_update_note(client, auth_headers):
    resp = client.post("/api/notes/", json={"content": "原始"}, headers=auth_headers)
    note_id = resp.json()["id"]

    resp = client.put(f"/api/notes/{note_id}", json={
        "content": "更新后", "code": "600519", "stock": "贵州茅台", "tag": "观察", "pinned": True,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "更新后"
    assert data["code"] == "600519"
    assert data["pinned"] is True


def test_delete_note(client, auth_headers):
    resp = client.post("/api/notes/", json={"content": "待删除"}, headers=auth_headers)
    note_id = resp.json()["id"]

    resp = client.delete(f"/api/notes/{note_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    resp = client.get("/api/notes/", headers=auth_headers)
    assert len(resp.json()) == 0


def test_toggle_pin(client, auth_headers):
    resp = client.post("/api/notes/", json={"content": "测试置顶"}, headers=auth_headers)
    note_id = resp.json()["id"]
    assert resp.json()["pinned"] is False

    resp = client.post(f"/api/notes/{note_id}/toggle-pin", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["pinned"] is True

    resp = client.post(f"/api/notes/{note_id}/toggle-pin", headers=auth_headers)
    assert resp.json()["pinned"] is False


def test_tags(client, auth_headers):
    client.post("/api/notes/", json={"content": "A", "tag": "宏观"}, headers=auth_headers)
    client.post("/api/notes/", json={"content": "B", "tag": "个股"}, headers=auth_headers)
    client.post("/api/notes/", json={"content": "C", "tag": "宏观"}, headers=auth_headers)

    resp = client.get("/api/notes/tags", headers=auth_headers)
    assert resp.status_code == 200
    tags = resp.json()
    assert "宏观" in tags
    assert "个股" in tags


def test_pinned_sorted_first(client, auth_headers):
    client.post("/api/notes/", json={"content": "普通A", "pinned": False}, headers=auth_headers)
    client.post("/api/notes/", json={"content": "置顶B", "pinned": True}, headers=auth_headers)
    client.post("/api/notes/", json={"content": "普通C", "pinned": False}, headers=auth_headers)

    resp = client.get("/api/notes/", headers=auth_headers)
    notes = resp.json()
    assert notes[0]["content"] == "置顶B"
    assert notes[0]["pinned"] is True


def test_empty_content_rejected(client, auth_headers):
    resp = client.post("/api/notes/", json={"content": ""}, headers=auth_headers)
    assert resp.status_code == 422
