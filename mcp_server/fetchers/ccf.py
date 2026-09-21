"""CCF 会议/期刊论文抓取"""
import time
import requests
from ..ccf_catalog import ALL_CCF_A
from ..ccf_catalog import BY_DBLP_KEY, BY_ABBR, Venue
DBLP_API = "https://dblp.org/search/publ/api"
REQUEST_INTERVAL = 1.5  # 秒，严格遵守 DBLP 频率限制

def fetch_venue_via_api(venue, year: int, store) -> int:
    """
    scheduler.py 用的封装：
      venue 可以是 Venue 对象、abbr 字符串、dblp_key 字符串
      抓取 -> 写库 -> 返回真正新增行数
    内部通过 fetch_venue_year() 已保证 REQUEST_INTERVAL 限速。
    """
    if isinstance(venue, Venue):
        v = venue
    elif isinstance(venue, str):
        v = BY_ABBR.get(venue.lower()) or BY_DBLP_KEY.get(venue)
        if v is None:
            raise ValueError(f"未知 venue: {venue!r}")
    else:
        raise TypeError(f"venue 类型不支持: {type(venue)}")

    papers = fetch_venue_year(v.dblp_key, year)

    # fetch_venue_year 在出错时返回 [{"error": ...}]，需要识别并抛出
    if papers and "error" in papers[0]:
        raise RuntimeError(papers[0]["error"])

    # 补齐 venue/area/kind 字段，供 store.upsert_many 使用
    for p in papers:
        p.setdefault("venue", v.abbr)
        p.setdefault("venue_kind", v.kind)
        p.setdefault("area", v.area)
        p["tags"] = v.tags   # 覆盖原 ccf.py 里只打 ccf-a/conference 的简陋 tags

    # 优先用新的 upsert_many，若 store 没有则退回 save
    if hasattr(store, "upsert_many"):
        return store.upsert_many(papers)
    return store.save(papers)
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
