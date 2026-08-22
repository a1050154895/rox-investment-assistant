"""本地知识库索引器（吸收自 ROX3.0 knowledge_base 的轻量思想，纯标准库重写）。

定位与边界：
- 只索引用户自行放入 data/knowledge/ 的文件（txt/md/docx），文件不进 git、
  不上传任何外部服务、默认不发送给 AI；
- 检索是"关键词 + 二元组"匹配（中文友好），不是语义检索——诚实降级，
  不假装 RAG；
- 知识库内容仅作研究参考素材，进入研究卡时仍需用户自行核验原文。
"""
from __future__ import annotations

import logging
import os
import re
import zipfile
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXT = (".txt", ".md", ".docx")
MAX_FILE_BYTES = 5 * 1024 * 1024  # 单文件 5MB 上限
SNIPPET_RADIUS = 40


def knowledge_dir() -> str:
    path = os.path.join(settings.DATA_DIR, "knowledge")
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class KnowledgeDoc:
    filename: str
    title: str
    text: str
    mtime: float

    def to_dict(self) -> dict:
        return {"filename": self.filename, "title": self.title, "chars": len(self.text)}


@dataclass
class KBIndex:
    docs: list[KnowledgeDoc] = field(default_factory=list)
    built_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "doc_count": len(self.docs),
            "built_at": self.built_at,
            "files": [d.to_dict() for d in self.docs],
        }


_INDEX = KBIndex()


def _read_docx(path: str) -> str:
    """docx 本质是 zip，直接读 word/document.xml 提取文本，无需第三方依赖。"""
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)
        return "".join(texts)
    except Exception as exc:  # noqa: BLE001 — 单文件损坏不拖垮整库
        logger.warning("docx 解析失败 %s: %s", path, exc)
        return ""


def _load_doc(path: str) -> KnowledgeDoc | None:
    if os.path.getsize(path) > MAX_FILE_BYTES:
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        text = _read_docx(path)
    else:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    if not text.strip():
        return None
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), os.path.basename(path))
    return KnowledgeDoc(
        filename=os.path.basename(path),
        title=first_line[:60],
        text=text,
        mtime=os.path.getmtime(path),
    )


def rebuild(directory: str | None = None) -> dict:
    """重建索引；目录不存在或为空时返回诚实空状态。"""
    directory = directory or knowledge_dir()
    docs: list[KnowledgeDoc] = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isfile(path) or not name.lower().endswith(SUPPORTED_EXT):
            continue
        doc = _load_doc(path)
        if doc:
            docs.append(doc)
    _INDEX.docs = docs
    _INDEX.built_at = __import__("time").time()
    return _INDEX.to_dict()


def _ensure_index() -> KBIndex:
    import time

    if not _INDEX.docs and _INDEX.built_at == 0.0:
        rebuild()
    elif _INDEX.built_at and time.time() - _INDEX.built_at > 600:
        rebuild()
    return _INDEX


def _terms(query: str) -> list[str]:
    """查询切词：英文/数字词 + 中文二元组，覆盖无分词器的中文匹配。"""
    terms = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{1,4}", query)
    out: list[str] = list(dict.fromkeys(t.strip() for t in terms if t.strip()))
    return out


def _snippet(text: str, pos: int) -> str:
    start = max(0, pos - SNIPPET_RADIUS)
    end = min(len(text), pos + SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    clean = text[start:end].replace("\n", " ")
    return f"{prefix}{clean}{suffix}"


def search(query: str, limit: int = 8) -> dict:
    """关键词检索：按命中次数排序，返回片段与出处。无结果时如实返回空。"""
    index = _ensure_index()
    terms = _terms(query)
    results = []
    for doc in index.docs:
        hits = 0
        snippets: list[str] = []
        for term in terms:
            count = doc.text.count(term)
            if count:
                hits += count
                pos = doc.text.find(term)
                if len(snippets) < 2:
                    snippets.append(_snippet(doc.text, pos))
        if hits:
            results.append({
                "filename": doc.filename,
                "title": doc.title,
                "hits": hits,
                "snippets": snippets,
            })
    results.sort(key=lambda r: r["hits"], reverse=True)
    return {
        "query": query,
        "results": results[:limit],
        "doc_count": len(index.docs),
        "method": "关键词+中文二元组匹配（非语义检索）；内容仅本地使用，默认不发送给 AI",
    }


def status() -> dict:
    return {**_ensure_index().to_dict(), "directory": knowledge_dir(),
            "note": "将 txt/md/docx 放入上述目录即可被索引；文件不入 git、不上传。"}
