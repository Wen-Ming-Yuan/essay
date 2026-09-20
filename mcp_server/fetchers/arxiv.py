"""arXiv 论文抓取"""
import time
import requests
import xml.etree.ElementTree as ET

ARXIV_API = "http://export.arxiv.org/api/query"
REQUEST_INTERVAL = 3.0  # arXiv 建议 3 秒间隔


def fetch_arxiv(category: str, keyword: str, max_results: int = 50) -> list[dict]:
    """
    抓取 arXiv 指定分类和关键词的最新论文。
    例如：fetch_arxiv("cs.CR", "fuzzing")
    """
    query = f"cat:{category} AND all:{keyword}"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    time.sleep(REQUEST_INTERVAL)
    try:
        resp = requests.get(ARXIV_API, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return [{"error": str(e), "category": category, "keyword": keyword}]

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
        summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
        published = entry.findtext("atom:published", "", ns)[:4]
        authors = [
            a.findtext("atom:name", "", ns)
            for a in entry.findall("atom:author", ns)
        ]
        link = entry.findtext("atom:id", "", ns)
        papers.append({
            "dblp_key": None,
            "title": title,
            "authors": authors,
            "venue": f"arXiv:{category}",
            "year": int(published) if published.isdigit() else None,
            "doi": "",
            "url": link,
            "abstract": summary,
            "source": "arxiv",
            "tags": ["arxiv", category],
        })
    return papers
