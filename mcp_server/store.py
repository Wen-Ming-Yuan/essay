"""论文存储层：SQLite 持久化"""
import sqlite3
import json
from pathlib import Path
from contextlib import closing

DB_PATH = Path(__file__).parent.parent / "papers.db"


class PaperStore:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
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
                    pdf_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            for idx in ["venue", "year", "tags", "source"]:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{idx} ON papers({idx})")
            # 兼容旧库：补齐缺失的 pdf_path 列
            try:
                conn.execute("ALTER TABLE papers ADD COLUMN pdf_path TEXT")
            except sqlite3.OperationalError:
                pass

    def save(self, papers: list[dict]) -> int:
        """批量保存，dblp_key 去重，返回新增数量"""
        inserted = 0
        with closing(sqlite3.connect(self.db_path)) as conn:
            for p in papers:
                if "error" in p:
                    continue
                tags = p.get("tags", [])
                if isinstance(tags, list):
                    tags = ",".join(tags)
                try:
                    cur = conn.execute("""
                        INSERT OR IGNORE INTO papers
                        (dblp_key, title, authors, venue, year, doi, url,
                         abstract, tags, source, pdf_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        p.get("pdf_path", ""),
                    ))
                    if cur.rowcount > 0:
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
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def by_venue(self, venue: str, limit: int = 500) -> list[dict]:
        return self.search("", venue=venue, limit=limit)

    def all(self, limit: int = 1000) -> list[dict]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM papers ORDER BY year DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with closing(sqlite3.connect(self.db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            by_venue = conn.execute(
                "SELECT venue, COUNT(*) as cnt FROM papers GROUP BY venue ORDER BY cnt DESC LIMIT 20"
            ).fetchall()
            by_year = conn.execute(
                "SELECT year, COUNT(*) as cnt FROM papers GROUP BY year ORDER BY year DESC LIMIT 10"
            ).fetchall()
            by_source = conn.execute(
                "SELECT source, COUNT(*) as cnt FROM papers GROUP BY source"
            ).fetchall()
        return {
            "total": total,
            "by_venue": [{"venue": v, "count": c} for v, c in by_venue],
            "by_year": [{"year": y, "count": c} for y, c in by_year],
            "by_source": [{"source": s, "count": c} for s, c in by_source],
        }
