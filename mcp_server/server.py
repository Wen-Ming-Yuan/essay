"""essay-paper-tracker MCP Server 入口"""
import sys

# ========== 必须在所有其他导入之前执行 ==========
sys.stdout = sys.stderr
# ================================================

import json
import logging
from fastmcp import FastMCP

from .store import PaperStore
from .fetchers.ccf import fetch_venue_year, fetch_all_ccf_a
from .fetchers.arxiv import fetch_arxiv
from .ccf_catalog import ALL_CCF_A

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("essay-mcp")

mcp = FastMCP("essay-paper-tracker")
store = PaperStore()


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


# ---------- Resources ----------

@mcp.resource("papers://all")
def resource_all_papers() -> str:
    """本地论文库的全部论文（最多1000条）"""
    return json.dumps(store.all(limit=1000), ensure_ascii=False)


@mcp.resource("papers://venue/{venue}")
def resource_papers_by_venue(venue: str) -> str:
    """指定会议/期刊的论文列表"""
    return json.dumps(store.by_venue(venue), ensure_ascii=False)


@mcp.resource("papers://stats")
def resource_stats() -> str:
    """论文库统计信息（按会议、年份）"""
    return json.dumps(store.stats(), ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
