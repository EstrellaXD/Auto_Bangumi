import asyncio

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
    keywords:list[str] = keywords.split(" ")

    # return await SearchTorrent().analyse_keyword(keywords=keywords, site=site)
    return EventSourceResponse(
        await SearchTorrent().analyse_keyword(keywords=keywords, site=site)
    )


@router.get(
    "/provider", response_model=list[str], dependencies=[Depends(get_current_user)]
)
async def search_provider():
    return list(SEARCH_CONFIG.keys())


if __name__ == "__main__":
    import json

    ans = asyncio.run(search_torrents(keywords="败北 ANI"))
    for i in list(ans):
        i = json.loads(i)
        print(i)
    # decoded_objects = []
    # for json_str in next(ans):
