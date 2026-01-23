from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from module.models import Bangumi
from module.searcher import SEARCH_CONFIG, SearchTorrent
from module.security.api import UNAUTHORIZED, get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "/bangumi", response_model=list[Bangumi], dependencies=[Depends(get_current_user)]
)
async def search_torrents(site: str = "mikan", keywords: str = Query(None)):
    """
    Server Send Event for per Bangumi item
    """
    if not keywords:
        return []
    keywords = keywords.split(" ")

    async def event_generator():
        async with SearchTorrent() as st:
            async for item in st.analyse_keyword(keywords=keywords, site=site):
                yield item

    return EventSourceResponse(content=event_generator())


@router.get(
    "/provider", response_model=list[str], dependencies=[Depends(get_current_user)]
)
async def search_provider():
    return list(SEARCH_CONFIG.keys())
