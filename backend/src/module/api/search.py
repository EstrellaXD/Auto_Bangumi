from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse

from module.searcher import SearchTorrent
from module.security.api import get_current_user, UNAUTHORIZED


router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
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
