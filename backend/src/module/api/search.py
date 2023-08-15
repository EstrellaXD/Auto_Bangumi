from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse

from module.searcher import SearchTorrent, SEARCH_CONFIG
from module.security.api import get_current_user, UNAUTHORIZED
from module.models import Torrent


router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=list[Torrent])
async def search_torrents(
    site: str = "mikan",
    keywords: str = Query(None),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise UNAUTHORIZED
    if not keywords:
        return []
    keywords = keywords.split(" ")
    with SearchTorrent() as st:
        return StreamingResponse(
            content=st.analyse_keyword(keywords=keywords, site=site),
            media_type="application/json",
        )


@router.get("/provider", response_model=list[str])
async def search_provider(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    return list(SEARCH_CONFIG.keys())
