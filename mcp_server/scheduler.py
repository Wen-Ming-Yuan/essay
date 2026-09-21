# mcp_server/scheduler.py
"""APScheduler 周任务：先尝试 DBLP API 做增量，失败则降级到本地 dump。"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from mcp_server.ccf_catalog import ALL_VENUES
from mcp_server.store import PaperStore
from mcp_server.fetchers.ccf import fetch_venue_via_api
from mcp_server.fetchers.dblp_dump import ingest as ingest_dump

log = logging.getLogger("essay.scheduler")

DUMP_PATH = Path(__file__).resolve().parents[1] / "data" / "dblp.nt.bz2"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "papers.db"


def weekly_update():
    store = PaperStore(DB_PATH)
    store.init_schema()
    this_year = datetime.now(timezone.utc).year

    for v in ALL_VENUES:
        last = store.get_fetch_state(v.abbr)          # {'last_year': 2024} or None
        start = (last["last_year"] + 1) if last else this_year - 1
        for year in range(start, this_year + 1):
            try:
                n = fetch_venue_via_api(v, year, store)   # 内部保证 sleep ≥ 1.5s
                store.set_fetch_state(v.abbr, year)
                log.info("%s %s: +%d", v.abbr, year, n)
            except Exception as e:                       # noqa: BLE001
                log.warning("%s %s 增量失败，等下次 dump 兜底: %s", v.abbr, year, e)
                break

    # 如果本地有新的月度 dump，做一次全量兜底
    if DUMP_PATH.exists():
        try:
            n = ingest_dump(DUMP_PATH, DB_PATH, this_year - 1, this_year)
            log.info("dump 兜底 upsert %d 篇", n)
        except Exception as e:                           # noqa: BLE001
            log.error("dump 兜底失败: %s", e)


def build_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="Asia/Shanghai")
    # 每周一 03:00
    sched.add_job(weekly_update, CronTrigger(day_of_week="mon", hour=3, minute=0),
                  id="ccf_weekly", replace_existing=True,
                  max_instances=1, coalesce=True, misfire_grace_time=3600)
    return sched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    s = build_scheduler()
    s.start()
    print("scheduler started; Ctrl-C to exit", file=sys.stderr)
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        s.shutdown()
