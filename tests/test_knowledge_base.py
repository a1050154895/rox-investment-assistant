"""本地知识库索引器测试。"""
import zipfile

from app.services.knowledge_base import rebuild, search, status


def _make_docx(path, text):
    """构造最小 docx（zip + document.xml）。"""
    with zipfile.ZipFile(path, "w") as zf:
        doc = f'<?xml version="1.0"?><w:document><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
        zf.writestr("word/document.xml", doc)


class TestKnowledgeBase:
    def test_index_and_search_txt_md(self, tmp_path):
        (tmp_path / "a.txt").write_text("债务危机的核心教训：债务周期决定信用扩张。", encoding="utf-8")
        (tmp_path / "b.md").write_text("# 交易心理\n持仓纪律比预测更重要。", encoding="utf-8")
        rebuild(str(tmp_path))
        res = search("债务周期")
        assert res["results"]
        assert res["results"][0]["filename"] == "a.txt"
        assert "债务" in res["results"][0]["snippets"][0]
        assert res["doc_count"] == 2

    def test_docx_parsing(self, tmp_path):
        _make_docx(str(tmp_path / "book.docx"), "投资最重要的事：风险控制优先于收益。")
        rebuild(str(tmp_path))
        res = search("风险控制")
        assert res["results"]
        assert res["results"][0]["filename"] == "book.docx"

    def test_no_match_returns_empty_honestly(self, tmp_path):
        (tmp_path / "a.txt").write_text("内容甲", encoding="utf-8")
        rebuild(str(tmp_path))
        res = search("不存在的关键词")
        assert res["results"] == []
        assert "非语义检索" in res["method"]

    def test_chinese_bigram_matching(self, tmp_path):
        (tmp_path / "c.txt").write_text("宏观流动性决定估值中枢。", encoding="utf-8")
        rebuild(str(tmp_path))
        assert search("流动性")["results"]
        assert search("估值")["results"]

    def test_ranking_by_hits(self, tmp_path):
        (tmp_path / "one.txt").write_text("止损 止损", encoding="utf-8")
        (tmp_path / "two.txt").write_text("止损 止损 止损 止损", encoding="utf-8")
        rebuild(str(tmp_path))
        res = search("止损")
        assert res["results"][0]["filename"] == "two.txt"
        assert res["results"][0]["hits"] == 4

    def test_status_reports_directory(self, tmp_path):
        rebuild(str(tmp_path))
        st = status()
        assert st["doc_count"] >= 0
        assert "不进 git" in st["note"] or "不入 git" in st["note"]

    def test_requires_auth(self, client):
        assert client.get("/api/knowledge/search?q=x").status_code == 401
        assert client.get("/api/knowledge/status").status_code == 401

    def test_api_search_flow(self, client, auth_headers, tmp_path, monkeypatch):
        from app.services import knowledge_base
        monkeypatch.setattr(knowledge_base, "rebuild", lambda d=None: rebuild(str(tmp_path)))
        (tmp_path / "d.txt").write_text("证据链思维：每个判断都要可追溯。", encoding="utf-8")
        rebuild(str(tmp_path))
        resp = client.get("/api/knowledge/search", params={"q": "证据链"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["results"]
