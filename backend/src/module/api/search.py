from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from module.conf.search_provider import get_provider, save_provider
from module.searcher import SearchTorrent, available_sites
from module.security.api import get_current_user

router = APIRouter(
    prefix="/search", tags=["search"], dependencies=[Depends(get_current_user)]
)



@router.get("/bangumi", response_class=EventSourceResponse)
async def search_torrents(
    site: str = "mikan", keywords: str = Query(None)
) -> AsyncIterator[ServerSentEvent]:
    """
    Server Send Event for per Bangumi item
    """
    if not keywords:
        return
    st = SearchTorrent()
    async for item in st.analyse_keyword(keywords=keywords.split(" "), site=site):
        yield ServerSentEvent(raw_data=item)


@router.get(
    "/provider", response_model=list[str]
)
async def search_provider():
    return list(available_sites())


@router.get(
    "/provider/config",
    response_model=dict[str, str],
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
)
async def update_search_provider_config(providers: dict[str, str]):
    """Update search providers configuration."""
    save_provider(providers)
    return {site: config["url"] for site, config in get_provider().items()}
