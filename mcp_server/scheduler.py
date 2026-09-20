from apscheduler.schedulers.background import BackgroundScheduler
from .fetchers.ccf import fetch_venue_year
from .store import PaperStore

scheduler = BackgroundScheduler()
store = PaperStore()

def weekly_fetch():
    """每周抓取一次当年 CCF A 类会议/期刊论文"""
    from datetime import datetime
    year = datetime.now().year
    from .ccf_catalog import ALL_CCF_A
    for key in ALL_CCF_A.values():
        papers = fetch_venue_year(key, year)
        store.save(papers)

scheduler.add_job(weekly_fetch, "cron", day_of_week="mon", hour=2)
scheduler.start()
