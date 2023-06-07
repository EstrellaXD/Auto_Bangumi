from fastapi import Depends, HTTPException, status

from module.manager import SeasonCollector
from module.models import BangumiData
from module.models.api import RssLink
from module.rss import analyser
from module.security import get_current_user

from .config import router


@router.post("/api/v1/download/analysis", tags=["download"])
async def analysis(link: RssLink, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    data = analyser.link_to_data(link.rss_link)
    if data:
        return data
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/download/collection", tags=["download"])
async def download_collection(
    data: BangumiData, current_user=Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if data:
        with SeasonCollector() as collector:
            if collector.collect_season(data, data.rss_link[0], proxy=True):
                return {"status": "Success"}
            else:
                return {"status": "Failed to add torrent"}
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/download/subscribe", tags=["download"])
async def subscribe(data: BangumiData, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if data:
        with SeasonCollector() as collector:
            collector.subscribe_season(data)
        return {"status": "Success"}
    else:
        return {"status": "Failed to parse link"}
