from .config import router

from module.models.api import *
from module.manager import FullSeasonGet
from module.rss import RSSAnalyser


def link_process(link):
    return RSSAnalyser().rss_to_data(link, full_parse=False)


@router.post("/api/v1/collection", tags=["download"])
async def collection(link: RssLink):
    data = link_process(link)
    if data:
        with FullSeasonGet() as season:
            season.download_collection(data[0], link)
        return data[0]
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/subscribe", tags=["download"])
async def subscribe(link: RssLink):
    data = link_process(link)
    if data:
        with FullSeasonGet() as season:
            season.add_subscribe(data[0], link)
        return data[0]
    else:
        return {"status": "Failed to parse link"}
