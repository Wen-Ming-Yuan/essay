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
    
    def init_schema(self) -> None:
        """幂等建表，dblp_dump.py / scheduler.py 调用。"""
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            dblp_key    TEXT PRIMARY KEY,
            title       TEXT,
            authors     TEXT,
            year        INTEGER,
            venue       TEXT,
            venue_kind  TEXT,
            area        TEXT,
            doi         TEXT,
            url         TEXT,
            tags        TEXT,
            source      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_papers_year  ON papers(year);
        CREATE INDEX IF NOT EXISTS idx_papers_venue ON papers(venue);
        CREATE INDEX IF NOT EXISTS idx_papers_area  ON papers(area);
        CREATE INDEX IF NOT EXISTS idx_papers_kind  ON papers(venue_kind);

        CREATE TABLE IF NOT EXISTS fetch_state (
            venue     TEXT PRIMARY KEY,
            last_year INTEGER,
            last_run  TIMESTAMP
        );
    """)
    self._conn.commit()


def upsert_many(self, rows: list[dict]) -> int:
    """
    批量写入，返回真正新插入行数。
    用 INSERT OR IGNORE 保证幂等，不会覆盖已有记录。
    """
    import json as _json

    payload = []
    for r in rows:
        key = r.get("dblp_key") or r.get("key") or ""
        title = r.get("title") or ""
        if not key or not title or "error" in r:
            continue

        authors = r.get("authors", [])
        if isinstance(authors, list):
            authors = _json.dumps(authors, ensure_ascii=False)

        tags = r.get("tags", [])
        if isinstance(tags, list):
            tags = ",".join(tags)

        payload.append({
            "dblp_key":   key,
            "title":      title,
            "authors":    authors,
            "year":       r.get("year"),
            "venue":      r.get("venue", ""),
            "venue_kind": r.get("venue_kind", ""),
            "area":       r.get("area", ""),
            "doi":        r.get("doi", ""),
            "url":        r.get("url", ""),
            "tags":       tags,
            "source":     r.get("source", "dblp"),
        })

    if not payload:
        return 0

    sql = """
        INSERT OR IGNORE INTO papers
        (dblp_key, title, authors, year, venue, venue_kind, area, doi, url, tags, source)
        VALUES (:dblp_key, :title, :authors, :year, :venue, :venue_kind,
                :area, :doi, :url, :tags, :source)
    """
    with self._conn:
        cur = self._conn.executemany(sql, payload)
    return cur.rowcount


def get_fetch_state(self, venue: str) -> dict | None:
    row = self._conn.execute(
        "SELECT last_year, last_run FROM fetch_state WHERE venue = ?",
        (venue,),
    ).fetchone()
    if not row:
        return None
    return {"last_year": row[0], "last_run": row[1]}


def set_fetch_state(self, venue: str, last_year: int) -> None:
    with self._conn:
        self._conn.execute(
            """INSERT INTO fetch_state (venue, last_year, last_run)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(venue) DO UPDATE
                 SET last_year = excluded.last_year,
                     last_run  = excluded.last_run""",
            (venue, last_year),
        )
