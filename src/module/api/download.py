from .config import router

from module.models.api import *
from module.models import BangumiData
from module.manager import FullSeasonGet
from module.rss import RSSAnalyser


def link_process(link):
    return RSSAnalyser().rss_to_data(link, full_parse=False)


@router.post("/api/v1/download/analysis", tags=["download"])
async def analysis(link: RssLink):
    data = link_process(link)
    if data:
        return data[0]
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/download/collection", tags=["download"])
async def download_collection(data: BangumiData):
    if data:
        with FullSeasonGet() as season:
            season.download_collection(data, data.rss_link)
        return {"status": "Success"}
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/download/subscribe", tags=["download"])
async def subscribe(data: BangumiData):
    if data:
        with FullSeasonGet() as season:
            season.add_subscribe(data)
        return {"status": "Success"}
    else:
        return {"status": "Failed to parse link"}
