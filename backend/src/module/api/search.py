from fastapi import APIRouter, Query, Depends
from sse_starlette.sse import EventSourceResponse

from module.searcher import SearchTorrent, SEARCH_CONFIG
from module.security.api import get_current_user, UNAUTHORIZED
from module.models import Bangumi


router = APIRouter(prefix="/search", tags=["search"])


@router.get("/bangumi", response_model=list[Bangumi], dependencies=[Depends(get_current_user)])
async def search_torrents(
    site: str = "mikan",
    keywords: str = Query(None)
):
    """
    Server Send Event for per Bangumi item
    """
    if not keywords:
        return []
    keywords = keywords.split(" ")
    with SearchTorrent() as st:
        return EventSourceResponse(
            content=st.analyse_keyword(keywords=keywords, site=site),
        )


@router.get("/provider", response_model=list[str], dependencies=[Depends(get_current_user)])
async def search_provider():
    return list(SEARCH_CONFIG.keys())
