"""CCF 会议/期刊论文抓取"""
import time
import requests
from ..ccf_catalog import ALL_CCF_A

DBLP_API = "https://dblp.org/search/publ/api"
REQUEST_INTERVAL = 1.5  # 秒，严格遵守 DBLP 频率限制


def fetch_venue_year(dblp_key: str, year: int) -> list[dict]:
    """
    按 DBLP key 和年份抓取论文。
    例如：fetch_venue_year("conf/ccs", 2025)
    """
    query = f"venue:{dblp_key}: year:{year}:"
    params = {"q": query, "format": "json", "h": 1000}
    headers = {"User-Agent": "essay-mcp/1.0 (research; contact@example.com)"}

    time.sleep(REQUEST_INTERVAL)
    try:
        resp = requests.get(DBLP_API, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [{"error": str(e), "venue": dblp_key, "year": year}]

    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    papers = []
    for h in hits:
        info = h.get("info", {})
        authors = info.get("authors", {}).get("author", [])
        if isinstance(authors, dict):
            authors = [authors]
        author_names = [a.get("text", "") for a in authors] if isinstance(authors, list) else []

        papers.append({
            "dblp_key": info.get("key", ""),
            "title": info.get("title", ""),
            "authors": author_names,
            "venue": info.get("venue", dblp_key),
            "year": int(info.get("year", year)),
            "doi": info.get("doi", ""),
            "url": info.get("ee", ""),
            "source": "dblp",
            "tags": ["ccf-a", "conference" if dblp_key.startswith("conf/") else "journal"],
        })
    return papers


def fetch_all_ccf_a(year: int) -> list[dict]:
    """抓取所有 CCF A 类会议和期刊在指定年份的论文"""
    all_papers = []
    for short, key in ALL_CCF_A.items():
        papers = fetch_venue_year(key, year)
        all_papers.extend(papers)
    return all_papers
