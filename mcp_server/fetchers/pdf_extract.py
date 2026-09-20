"""PDF 元数据提取：标题、作者、摘要、DOI"""
import re
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("essay-mcp.pdf")


def extract_pdf_metadata(pdf_path: str) -> Dict:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"error": "pypdf 未安装，请运行 pip install pypdf"}

    path = Path(pdf_path)
    if not path.exists():
        return {"error": f"文件不存在: {pdf_path}"}
    if path.suffix.lower() != ".pdf":
        return {"error": f"不是 PDF 文件: {pdf_path}"}

    try:
        reader = PdfReader(str(path))
        meta = reader.metadata or {}
        title = (meta.get("/Title") or "").strip()
        author = (meta.get("/Author") or "").strip()

        max_pages = min(3, len(reader.pages))
        head_text = "\n".join((reader.pages[i].extract_text() or "") for i in range(max_pages))

        if not title:
            title = _guess_title(head_text)

        abstract = _extract_abstract(head_text)
        doi = _extract_doi(head_text)

        authors = []
        if author:
            authors = [a.strip() for a in re.split(r"[,;]", author) if a.strip()]

        return {
            "title": title, "authors": authors, "abstract": abstract,
            "doi": doi, "pdf_path": str(path.resolve()),
            "source": "pdf", "num_pages": len(reader.pages),
            "tags": ["pdf", "local"],
        }
    except Exception as e:
        logger.error(f"PDF 解析失败 {pdf_path}: {e}")
        return {"error": str(e)}


def extract_multiple(pdf_dir: str, pattern: str = "*.pdf") -> List[Dict]:
    dir_path = Path(pdf_dir)
    if not dir_path.is_dir():
        return [{"error": f"不是目录: {pdf_dir}"}]
    return [extract_pdf_metadata(str(p)) for p in dir_path.glob(pattern)]


def _guess_title(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:15]:
        low = line.lower()
        if 10 < len(line) < 250 and not low.startswith(
            ("arxiv", "doi", "http", "www", "proceedings", "copyright", "preprint")
        ):
            return line
    return ""


def _extract_abstract(text: str) -> str:
    m = re.search(
        r"abstract[\s:]*\n?(.*?)(?:\n\s*(?:1\.?\s*)?introduction|"
        r"\n\s*keywords|\n\s*ccs concepts|\n\s*1\s+introduction)",
        text, re.IGNORECASE | re.DOTALL,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:3000]
    m2 = re.search(
        r"((?:this paper|we propose|we present|in this work)[^.]{50,1500}\.)",
        text, re.IGNORECASE,
    )
    if m2:
        return re.sub(r"\s+", " ", m2.group(1)).strip()
    return ""


def _extract_doi(text: str) -> str:
    m = re.search(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", text, re.IGNORECASE)
    return m.group(1) if m else ""
