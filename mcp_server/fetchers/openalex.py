import requests
from typing import List, Dict

OPENALEX_API = "https://api.openalex.org/works"

def fetch_openalex(keyword: str, from_date: str = None, per_page: int = 25) -> List[Dict]:
    """从 OpenAlex 抓取指定关键词的最新论文"""
    params = {
        "search": keyword,
        "per-page": per_page,
        "sort": "publication_date:desc"
    }
    if from_date:
        params["filter"] = f"from_publication_date:{from_date}"
    
    resp = requests.get(OPENALEX_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    papers = []
    for work in data.get("results", []):
        authors = [a.get("author", {}).get("display_name", "") 
                   for a in work.get("authorships", [])]
        papers.append({
            "dblp_key": None,
            "title": work.get("title", ""),
            "authors": authors,
            "venue": work.get("host_venue", {}).get("display_name", ""),
            "year": int(work.get("publication_year", 0)),
            "doi": work.get("doi", "").replace("https://doi.org/", ""),
            "url": work.get("doi", ""),
            "abstract": work.get("abstract_inverted_index", {}),
            "source": "openalex",
            "tags": ["openalex"]
        })
    return papers
