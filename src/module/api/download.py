from .config import router

from module.models.api import *
from module.models import BangumiData
from module.manager import SeasonCollector
from module.rss import analyser


def link_process(link):
    return analyser.rss_to_data(link, full_parse=False)


@router.post("/api/v1/download/analysis", tags=["download"])
async def analysis(link: RssLink):
    data = link_process(link.rss_link)
    if data:
        return data[0]
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/download/collection", tags=["download"])
async def download_collection(data: BangumiData):
    if data:
        with SeasonCollector() as collector:
            collector.collect_season(data, data.rss_link[0])
        return {"status": "Success"}
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/download/subscribe", tags=["download"])
async def subscribe(data: BangumiData):
    if data:
        with SeasonCollector() as collector:
            collector.subscribe_season(data)
        return {"status": "Success"}
    else:
        return {"status": "Failed to parse link"}
