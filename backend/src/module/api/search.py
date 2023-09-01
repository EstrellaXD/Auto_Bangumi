from fastapi import APIRouter, Query, Depends
from sse_starlette.sse import EventSourceResponse

from module.searcher import SearchTorrent, SEARCH_CONFIG
from module.security.api import get_current_user, UNAUTHORIZED
from module.models import Bangumi


router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=EventSourceResponse[Bangumi])
async def search_torrents(
    site: str = "mikan",
    keywords: str = Query(None),
    current_user=Depends(get_current_user),
):
    """
    Server Send Event for per Bangumi item
    """
    if not current_user:
        raise UNAUTHORIZED
    if not keywords:
        return []
    keywords = keywords.split(" ")
    with SearchTorrent() as st:
        return EventSourceResponse(
            content=st.analyse_keyword(keywords=keywords, site=site),
        )


@router.get("/provider", response_model=list[str])
async def search_provider(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    return list(SEARCH_CONFIG.keys())
