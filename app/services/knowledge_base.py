"""本地知识库索引器（吸收自 ROX3.0 knowledge_base 的轻量思想）。

定位与边界：
- 只索引用户自行放入 data/knowledge/ 的文件（txt/md/docx/pdf），文件不进 git、
  不上传任何外部服务、默认不发送给 AI；
- PDF 解析用可选依赖 pypdf（纯 Python、本地解析）；未安装时 PDF 被跳过并在
  状态里如实说明，其余格式不受影响（txt/md/docx 仍为纯标准库实现）；
- 检索是"关键词 + 二元组"匹配（中文友好），不是语义检索——诚实降级，
  不假装 RAG；命中文本以 [[ ]] 标记包裹，由前端转义后渲染为高亮；
- 知识库内容仅作研究参考素材，进入研究卡时仍需用户自行核验原文。
"""
from __future__ import annotations

import logging
import os
import re
import time
import zipfile
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)

try:  # 可选依赖：未安装时 PDF 诚实跳过
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:  # pragma: no cover - 取决于环境
    PdfReader = None
    PDF_SUPPORT = False

SUPPORTED_EXT = (".txt", ".md", ".docx", ".pdf")
MAX_FILE_BYTES = 10 * 1024 * 1024  # 单文件 10MB 上限（PDF 通常更大）
SNIPPET_RADIUS = 40
_MAX_SNIPPETS = 3


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
    skipped: list[str] = field(default_factory=list)

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


def _read_pdf(path: str) -> str:
    """pypdf 逐页提取文本；未安装或解析失败时返回空（由调用方如实跳过）。"""
    if not PDF_SUPPORT:
        return ""
    try:
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:  # noqa: BLE001 — 单文件损坏不拖垮整库
        logger.warning("pdf 解析失败 %s: %s", path, exc)
        return ""


def _load_doc(path: str) -> KnowledgeDoc | None:
    if os.path.getsize(path) > MAX_FILE_BYTES:
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        text = _read_docx(path)
    elif ext == ".pdf":
        text = _read_pdf(path)
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
    skipped: list[str] = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isfile(path) or not name.lower().endswith(SUPPORTED_EXT):
            continue
        doc = _load_doc(path)
        if doc:
            docs.append(doc)
        elif name.lower().endswith(".pdf") and not PDF_SUPPORT:
            skipped.append(name)
    _INDEX.docs = docs
    _INDEX.skipped = skipped
    _INDEX.built_at = time.time()
    return _INDEX.to_dict()


def _ensure_index() -> KBIndex:
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


def _snippet(text: str, terms: list[str]) -> str:
    """取包含关键词的上下文片段；命中的词用 [[ ]] 标记（前端转义后渲染高亮）。"""
    positions = sorted(
        {m.start() for term in terms for m in re.finditer(re.escape(term), text)}
    )
    if not positions:
        return ""
    # 合并相邻命中的采样窗口，最多取 _MAX_SNIPPETS 段
    windows: list[int] = []
    for pos in positions:
        if not windows or pos - windows[-1] > SNIPPET_RADIUS * 2:
            windows.append(pos)
    parts: list[str] = []
    for start in windows[:_MAX_SNIPPETS]:
        lo = max(0, start - SNIPPET_RADIUS)
        hi = min(len(text), start + SNIPPET_RADIUS * 2)
        seg = text[lo:hi].replace("\n", " ")
        for term in sorted({t for t in terms if t}, key=len, reverse=True):
            seg = seg.replace(term, f"[[{term}]]")
        prefix = "…" if lo > 0 else ""
        suffix = "…" if hi < len(text) else ""
        parts.append(f"{prefix}{seg}{suffix}")
    return "\n".join(parts)


def search(query: str, limit: int = 8) -> dict:
    """关键词检索：按命中次数排序，返回带高亮标记的片段与出处。无结果时如实返回空。"""
    index = _ensure_index()
    terms = _terms(query)
    results = []
    for doc in index.docs:
        hits = 0
        for term in terms:
            hits += doc.text.count(term)
        if hits:
            results.append({
                "filename": doc.filename,
                "title": doc.title,
                "hits": hits,
                "snippets": _snippet(doc.text, terms).split("\n") if terms else [],
            })
    results.sort(key=lambda r: r["hits"], reverse=True)
    return {
        "query": query,
        "results": results[:limit],
        "doc_count": len(index.docs),
        "method": "关键词+中文二元组匹配（非语义检索）；内容仅本地使用，默认不发送给 AI",
    }


def status() -> dict:
    index = _ensure_index()
    note = "将 txt/md/docx/pdf 放入上述目录即可被索引；文件不入 git、不上传。"
    if index.skipped:
        note += f" {len(index.skipped)} 个 PDF 未索引（需安装 pypdf：pip install pypdf）。"
    return {**index.to_dict(), "directory": knowledge_dir(), "pdf_support": PDF_SUPPORT,
            "skipped_pdfs": index.skipped, "note": note}
