"""essay-paper-tracker MCP Server 入口"""
import sys
_original_stdout = sys.stdout
# ========== 必须在所有其他导入之前执行 ==========
sys.stdout = sys.stderr
# ... 之后在 mcp.run() 前恢复
# ================================================

import json
import logging
from fastmcp import FastMCP

from .store import PaperStore
from .fetchers.ccf import fetch_venue_year, fetch_all_ccf_a
from .fetchers.arxiv import fetch_arxiv
from .ccf_catalog import ALL_CCF_A
from .fetchers.pdf_extract import extract_pdf_metadata, extract_multiple
from .atlas import AtlasEmbedder

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("essay-mcp")

mcp = FastMCP("essay-paper-tracker")
store = PaperStore()
atlas = AtlasEmbedder()

# ---------- Tools ----------

@mcp.tool()
def fetch_ccf_venue(dblp_key: str, year: int) -> str:
    """抓取指定CCF A类会议/期刊在指定年份的论文。
    dblp_key 例如 'conf/ccs' 或 'journals/tdsc'。"""
    papers = fetch_venue_year(dblp_key, year)
    inserted = store.save(papers)
    return json.dumps({
        "venue": dblp_key,
        "year": year,
        "fetched": len(papers),
        "inserted": inserted,
    }, ensure_ascii=False)


@mcp.tool()
def fetch_arxiv_papers(category: str, keyword: str, max_results: int = 50) -> str:
    """抓取 arXiv 指定分类和关键词的最新论文。例如 category='cs.CR', keyword='fuzzing'。"""
    papers = fetch_arxiv(category, keyword, max_results)
    inserted = store.save(papers)
    return json.dumps({
        "category": category,
        "keyword": keyword,
        "fetched": len(papers),
        "inserted": inserted,
    }, ensure_ascii=False)


@mcp.tool()
def search_papers(keyword: str, venue: str = None, year: int = None, limit: int = 50) -> str:
    """在本地论文库中按关键词、会议、年份筛选。"""
    results = store.search(keyword, venue=venue, year=year, limit=limit)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def list_ccf_a_venues() -> str:
    """列出所有已登记的 CCF A 类会议/期刊及其 DBLP key。"""
    return json.dumps(ALL_CCF_A, ensure_ascii=False, indent=2)
# ---------- PDF 处理 ----------

@mcp.tool()
def extract_pdf(pdf_path: str) -> str:
    """从本地 PDF 文件提取标题、作者、摘要、DOI。"""
    meta = extract_pdf_metadata(pdf_path)
    return json.dumps(meta, ensure_ascii=False)


@mcp.tool()
def ingest_pdf(pdf_path: str) -> str:
    """提取 PDF 元数据并存入本地论文库。"""
    meta = extract_pdf_metadata(pdf_path)
    if "error" in meta:
        return json.dumps(meta, ensure_ascii=False)
    inserted = store.save([meta])
    return json.dumps({
        "inserted": inserted,
        "title": meta.get("title", ""),
        "pdf_path": meta.get("pdf_path", ""),
    }, ensure_ascii=False)


@mcp.tool()
def scan_pdf_directory(pdf_dir: str) -> str:
    """扫描指定目录下的所有 PDF 文件并返回元数据列表（不入库）。"""
    results = extract_multiple(pdf_dir)
    valid = [r for r in results if "error" not in r]
    return json.dumps({
        "total": len(results), "valid": len(valid), "papers": valid,
    }, ensure_ascii=False)


# ---------- 语义地图 ----------

@mcp.tool()
def build_atlas(keyword: str = "", venue: str = None, max_papers: int = 300) -> str:
    """构建论文语义地图：向量化摘要并投影到 2D 空间。
    返回每个点的坐标、标题、作者、标签，可用于前端可视化。"""
    if keyword:
        papers = store.search(keyword, venue=venue, limit=max_papers)
    else:
        papers = store.all(limit=max_papers)
    if not papers:
        return json.dumps({"points": [], "count": 0, "warning": "论文库为空"}, ensure_ascii=False)
    try:
        result = atlas.build_atlas(papers, max_papers=max_papers)
        return json.dumps(result, ensure_ascii=False)
    except ImportError as e:
        return json.dumps({"error": str(e), "hint": "pip install sentence-transformers umap-learn"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"构建语义地图失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

# ---------- Resources ----------

@mcp.resource("papers://all")
def resource_all_papers() -> str:
    """本地论文库的全部论文（最多100000条）"""
    return json.dumps(store.all(limit=100000), ensure_ascii=False)


@mcp.resource("papers://venue/{venue}")
def resource_papers_by_venue(venue: str) -> str:
    """指定会议/期刊的论文列表"""
    return json.dumps(store.by_venue(venue), ensure_ascii=False)


@mcp.resource("papers://stats")
def resource_stats() -> str:
    """论文库统计信息（按会议、年份）"""
    return json.dumps(store.stats(), ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
