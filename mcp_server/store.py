"""论文存储层：SQLite 持久化"""
import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "papers.db"


class PaperStore:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dblp_key TEXT UNIQUE,
                    title TEXT NOT NULL,
                    authors TEXT,
                    venue TEXT,
                    year INTEGER,
                    doi TEXT,
                    url TEXT,
                    abstract TEXT,
                    tags TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_venue ON papers(venue)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON papers(year)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON papers(tags)")

    def save(self, papers: list[dict]) -> int:
        """批量保存，dblp_key 去重，返回新增数量"""
        inserted = 0
        with sqlite3.connect(self.db_path) as conn:
            for p in papers:
                tags = p.get("tags", [])
                if isinstance(tags, list):
                    tags = ",".join(tags)
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO papers
                        (dblp_key, title, authors, venue, year, doi, url, abstract, tags, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("dblp_key"),
                        p.get("title", ""),
                        json.dumps(p.get("authors", []), ensure_ascii=False),
                        p.get("venue", ""),
                        p.get("year"),
                        p.get("doi", ""),
                        p.get("url", ""),
                        p.get("abstract", ""),
                        tags,
                        p.get("source", ""),
                    ))
                    if conn.total_changes:
                        inserted += 1
                except sqlite3.Error:
                    continue
        return inserted

    def search(self, keyword: str, venue: str = None, year: int = None, limit: int = 100) -> list[dict]:
        """按关键词、会议、年份筛选"""
        sql = "SELECT * FROM papers WHERE (title LIKE ? OR abstract LIKE ?)"
        params = [f"%{keyword}%", f"%{keyword}%"]
        if venue:
            sql += " AND venue = ?"
            params.append(venue)
        if year:
            sql += " AND year = ?"
            params.append(year)
        sql += " ORDER BY year DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def by_venue(self, venue: str, limit: int = 500) -> list[dict]:
        return self.search("", venue=venue, limit=limit)

    def all(self, limit: int = 1000) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM papers ORDER BY year DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            by_venue = conn.execute(
                "SELECT venue, COUNT(*) as cnt FROM papers GROUP BY venue ORDER BY cnt DESC LIMIT 20"
            ).fetchall()
            by_year = conn.execute(
                "SELECT year, COUNT(*) as cnt FROM papers GROUP BY year ORDER BY year DESC LIMIT 10"
            ).fetchall()
        return {
            "total": total,
            "by_venue": [{"venue": v, "count": c} for v, c in by_venue],
            "by_year": [{"year": y, "count": c} for y, c in by_year],
        }
