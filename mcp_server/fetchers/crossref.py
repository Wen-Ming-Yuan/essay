import requests
from typing import List, Dict

CROSSREF_API = "https://api.crossref.org/works"

def fetch_crossref(keyword: str, rows: int = 25) -> List[Dict]:
    """从 Crossref 抓取指定关键词的最新论文"""
    params = {
        "query": keyword,
        "rows": rows,
        "sort": "published",
        "order": "desc"
    }
    
    resp = requests.get(CROSSREF_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    papers = []
    for item in data.get("message", {}).get("items", []):
        authors = [f"{a.get('given', '')} {a.get('family', '')}".strip()
                   for a in item.get("author", [])]
        pub_date = item.get("published", {}).get("date-parts", [[None]])[0]
        year = pub_date[0] if pub_date else None
        
        papers.append({
            "dblp_key": None,
            "title": item.get("title", [""])[0],
            "authors": authors,
            "venue": item.get("container-title", [""])[0],
            "year": year,
            "doi": item.get("DOI", ""),
            "url": item.get("URL", ""),
            "abstract": item.get("abstract", ""),
            "source": "crossref",
            "tags": ["crossref"]
        })
    return papers
