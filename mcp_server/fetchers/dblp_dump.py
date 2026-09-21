# mcp_server/fetchers/dblp_dump.py
"""
从 DBLP N-Triples 月度转储本地过滤 CCF-A 论文。
版本无关 DOI: https://doi.org/10.4230/dblp.rdf.ntriples

设计：两遍扫描。
  Pass 1  只收 subject_uri 与 (venue_stream, year)，内存里只有 URI 集合。
  Pass 2  只对命中 subject 解析 title/author/doi/url 并落库。
原因：单遍解析会把几十万篇论文的全文属性同时驻留内存，直接 OOM。
"""

from __future__ import annotations

import bz2
import gzip
import re
import sys
from pathlib import Path
from typing import Iterable, Iterator

# 允许 `python -m mcp_server.fetchers.dblp_dump` 与直接运行两种方式
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp_server.ccf_catalog import BY_STREAM, Venue  # noqa: E402
from mcp_server.store import PaperStore             # noqa: E402

# ── N-Triples 行解析（手写正则，比 rdflib 快一个量级）────────────────
# <s> <p> <o> .       或   <s> <p> "lit"^^<dt> .
_TRIPLE_RE = re.compile(
    r'^(?P<s><[^>]+>)\s+(?P<p><[^>]+>)\s+(?P<o>.+?)\s*\.\s*$'
)
_IRI_RE = re.compile(r'^<(?P<iri>[^>]+)>$')
_LIT_RE = re.compile(r'^"(?P<val>(?:[^"\\]|\\.)*)"')   # 忽略 lang/datatype

P_STREAM = "<https://dblp.org/rdf/schema#publishedIn>"
P_YEAR   = "<https://dblp.org/rdf/schema#yearOfPublication>"
P_TITLE  = "<https://dblp.org/rdf/schema#title>"
P_AUTHOR = "<https://dblp.org/rdf/schema#author>"
P_DOI    = "<https://dblp.org/rdf/schema#doi>"
P_URL    = "<https://dblp.org/rdf/schema#url>"
P_ORDER  = "<https://dblp.org/rdf/schema#authorOrder>"  # 可选，用于排序


def _open_maybe_compressed(path: Path):
    """自动识别 .gz / .bz2 / 纯文本。"""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    if path.suffix == ".bz2":
        return bz2.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def _iri(raw: str) -> str | None:
    m = _IRI_RE.match(raw)
    return m.group("iri") if m else None


def _lit(raw: str) -> str | None:
    m = _LIT_RE.match(raw)
    if not m:
        return None
    return m.group("val").encode("utf-8").decode("unicode_escape")


def _stream_year(raw: str) -> int | None:
    lit = _lit(raw)
    if lit is None:
        return None
    try:
        return int(lit[:4])
    except ValueError:
        return None


# ── Pass 1 ─────────────────────────────────────────────────────────
def pass1_index(
    dump_path: Path,
    year_from: int,
    year_to: int,
    wanted_streams: set[str] | None = None,
) -> dict[str, tuple[str, int]]:
    """
    返回 {subject_uri: (venue_stream_url, year)}。
    只解析 publishedIn 与 yearOfPublication 两个谓词。
    """
    streams = wanted_streams or set(BY_STREAM)
    hits: dict[str, tuple[str, int]] = {}
    # 暂存每个 subject 的 stream / year，等两个都到齐再落 hits
    pending_stream: dict[str, str] = {}
    pending_year: dict[str, int] = {}

    n = 0
    with _open_maybe_compressed(dump_path) as fh:
        for line in fh:
            n += 1
            if n % 5_000_000 == 0:
                print(f"[pass1] {n/1e6:.0f}M lines, hits={len(hits)}", file=sys.stderr)
            m = _TRIPLE_RE.match(line)
            if not m:
                continue
            pred = m.group("p")
            if pred == P_STREAM:
                s = m.group("s")
                stream = _iri(m.group("o"))
                if stream in streams:
                    pending_stream[s] = stream
                    y = pending_year.pop(s, None)
                    if y is not None and year_from <= y <= year_to:
                        hits[s] = (stream, y)
                else:
                    # 不是目标 venue，清掉可能残留的 pending
                    pending_stream.pop(s, None)
            elif pred == P_YEAR:
                s = m.group("s")
                if s in pending_stream:
                    y = _stream_year(m.group("o"))
                    if y is not None:
                        if year_from <= y <= year_to:
                            hits[s] = (pending_stream[s], y)
                        pending_stream.pop(s, None)
                        pending_year.pop(s, None)
                else:
                    y = _stream_year(m.group("o"))
                    if y is not None:
                        pending_year[s] = y
    print(f"[pass1] done. lines={n} hits={len(hits)}", file=sys.stderr)
    return hits


# ── Pass 2 ─────────────────────────────────────────────────────────
def pass2_extract(
    dump_path: Path,
    hits: dict[str, tuple[str, int]],
) -> Iterator[dict]:
    """
    流式产出论文 dict。只处理 hits 里的 subject，其余行直接跳过。
    """
    buf: dict[str, dict] = {}

    def flush(subject: str) -> dict | None:
        rec = buf.pop(subject, None)
        if not rec:
            return None
        stream, year = hits[subject]
        venue: Venue = BY_STREAM[stream]
        return {
            "dblp_key": subject,
            "title": rec.get("title"),
            "authors": rec.get("authors", []),
            "year": year,
            "venue": venue.abbr,
            "venue_kind": venue.kind,
            "area": venue.area,
            "doi": rec.get("doi"),
            "url": rec.get("url"),
            "tags": venue.tags,
        }

    with _open_maybe_compressed(dump_path) as fh:
        for line in fh:
            m = _TRIPLE_RE.match(line)
            if not m:
                continue
            s = m.group("s")
            if s not in hits:
                continue
            pred = m.group("p")
            if pred == P_TITLE:
                buf.setdefault(s, {})["title"] = _lit(m.group("o"))
            elif pred == P_AUTHOR:
                a = _lit(m.group("o"))
                if a:
                    buf.setdefault(s, {}).setdefault("authors", []).append(a)
            elif pred == P_DOI:
                buf.setdefault(s, {})["doi"] = _lit(m.group("o"))
            elif pred == P_URL:
                buf.setdefault(s, {})["url"] = _lit(m.group("o"))
            elif pred == P_STREAM:
                # 见到 stream 说明这个 subject 的块快结束了
                rec = flush(s)
                if rec and rec.get("title"):
                    yield rec


# ── 对外入口 ────────────────────────────────────────────────────────
def ingest(
    dump_path: str | Path,
    db_path: str | Path,
    year_from: int,
    year_to: int,
) -> int:
    dump_path, db_path = Path(dump_path), Path(db_path)
    store = PaperStore(db_path)
    store.init_schema()

    hits = pass1_index(dump_path, year_from, year_to)
    written = 0
    batch: list[dict] = []
    for rec in pass2_extract(dump_path, hits):
        batch.append(rec)
        if len(batch) >= 500:
            written += store.upsert_many(batch)
            batch.clear()
    if batch:
        written += store.upsert_many(batch)
    return written


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("dump", help="dblp.nt / dblp.nt.gz / dblp.nt.bz2")
    ap.add_argument("--db", default="papers.db")
    ap.add_argument("--from-year", type=int, required=True)
    ap.add_argument("--to-year", type=int, required=True)
    args = ap.parse_args()

    n = ingest(args.dump, args.db, args.from_year, args.to_year)
    print(f"upserted {n} papers -> {args.db}", file=sys.stderr)
