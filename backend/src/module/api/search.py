from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from module.conf.search_provider import get_provider, save_provider
from module.searcher import SEARCH_CONFIG, SearchTorrent
from module.security.api import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/bangumi", dependencies=[Depends(get_current_user)])
async def search_torrents(site: str = "mikan", keywords: str = Query(None)):
    """
    Server Send Event for per Bangumi item
    """
    if not keywords:
        return []
    keyword_list = keywords.split(" ")

    async def event_generator():
        st = SearchTorrent()
        async for item in st.analyse_keyword(keywords=keyword_list, site=site):
            yield item

    return EventSourceResponse(content=event_generator())


@router.get(
    "/provider", response_model=list[str], dependencies=[Depends(get_current_user)]
)
async def search_provider():
    return list(SEARCH_CONFIG.keys())


@router.get(
    "/provider/config",
    response_model=dict[str, str],
    dependencies=[Depends(get_current_user)],
)
async def get_search_provider_config():
    """Get all search providers with their URL templates.

    Each provider is stored internally as {url, parser}; only the URL is
    exposed here to keep this endpoint's contract unchanged for callers.
    """
    return {site: config["url"] for site, config in get_provider().items()}


@router.put(
    "/provider/config",
    response_model=dict[str, str],
    dependencies=[Depends(get_current_user)],
)
async def update_search_provider_config(providers: dict[str, str]):
    """Update search providers configuration."""
    save_provider(providers)
    return {site: config["url"] for site, config in get_provider().items()}
