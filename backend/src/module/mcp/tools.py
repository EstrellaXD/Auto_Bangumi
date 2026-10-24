"""内置 MCP 工具：参数 schema 由类型注解生成。

``structured_output=False``：结果由 ``AutoBangumiMCP.call_tool`` 序列化为一段
JSON 文本，不声明 outputSchema。
"""

import json
from typing import Annotated, Literal

from pydantic import Field

from module.conf import VERSION
from module.database import Database
from module.downloader import DownloaderPool, list_torrents
from module.manager import SeasonCollector, TorrentManager
from module.models import Bangumi, BangumiUpdate, RSSItem
from module.rss import RSSAnalyser, RSSEngine
from module.searcher import SearchTorrent

from .runtime import get_context
from .server import mcp

Site = Literal["mikan", "dmhy", "nyaa"]


def _bangumi_to_dict(b: Bangumi) -> dict:
    return {
        "id": b.id,
        "official_title": b.official_title,
        "title_raw": b.title_raw,
        "season": b.season,
        "group_name": b.group_name,
        "dpi": b.dpi,
        "source": b.source,
        "subtitle": b.subtitle,
        "episode_offset": b.episode_offset,
        "season_offset": b.season_offset,
        "filter": b.filter,
        "rss_link": b.rss_link,
        "poster_link": b.poster_link,
        "added": b.added,
        "save_path": b.save_path,
        "deleted": b.deleted,
        "archived": b.archived,
        "eps_collect": b.eps_collect,
    }


@mcp.tool(
    description="List all tracked anime subscriptions. Returns title, season, status, and episode offset for each.",
    structured_output=False,
)
async def list_anime(
    active_only: Annotated[
        bool,
        Field(description="If true, only return active (non-disabled) anime"),
    ] = False,
) -> list[dict]:
    async with Database() as db:
        manager = TorrentManager(db)
        if active_only:
            items = await manager.search_all_bangumi()
        else:
            items = await db.bangumi.search_all()
    return [_bangumi_to_dict(b) for b in items]


@mcp.tool(
    description="Get detailed information about a specific anime subscription by its ID.",
    structured_output=False,
)
async def get_anime(
    id: Annotated[int, Field(description="The anime/bangumi ID")],
) -> dict:
    async with Database() as db:
        manager = TorrentManager(db)
        result = await manager.search_one(id)
    if isinstance(result, Bangumi):
        return _bangumi_to_dict(result)
    return {"error": result.msg_en}


@mcp.tool(
    description="Search for anime torrents across torrent sites (Mikan, DMHY, Nyaa). Returns available anime matching the keywords.",
    structured_output=False,
)
async def search_anime(
    keywords: Annotated[str, Field(description="Search keywords (e.g. anime title)")],
    site: Annotated[Site, Field(description="Torrent site to search")] = "mikan",
) -> list[dict]:
    keyword_list = keywords.split()
    results = []
    st = SearchTorrent()
    async for item_json in st.analyse_keyword(keywords=keyword_list, site=site):
        results.append(json.loads(item_json))
        if len(results) >= 20:
            break
    return results


@mcp.tool(
    description="Subscribe to an anime series by providing its RSS link. Analyzes the RSS feed and sets up automatic downloading.",
    structured_output=False,
)
async def subscribe_anime(
    rss_link: Annotated[
        str,
        Field(
            description="RSS feed URL for the anime (obtained from search_anime results)"
        ),
    ],
    parser: Annotated[Site, Field(description="RSS parser type")] = "mikan",
) -> dict:
    analyser = RSSAnalyser()
    rss = RSSItem(url=rss_link, parser=parser)
    data = await analyser.link_to_data(rss)
    if not isinstance(data, Bangumi):
        return {"error": data.msg_en if hasattr(data, "msg_en") else str(data)}
    resp = await SeasonCollector.subscribe_season(data, parser=parser)
    return {"status": resp.status, "message": resp.msg_en}


@mcp.tool(
    description="Unsubscribe from an anime. Can either disable (keeps data) or fully delete the subscription.",
    structured_output=False,
)
async def unsubscribe_anime(
    id: Annotated[int, Field(description="The anime/bangumi ID to unsubscribe")],
    delete: Annotated[
        bool,
        Field(
            description="If true, permanently delete the subscription. If false, just disable it."
        ),
    ] = False,
) -> dict:
    async with Database() as db:
        manager = TorrentManager(db)
        if delete:
            resp = await manager.delete_rule(id)
        else:
            resp = await manager.disable_rule(id)
    return {"status": resp.status, "message": resp.msg_en}


@mcp.tool(
    description="Show current torrent download status from the download client (qBittorrent/Aria2).",
    structured_output=False,
)
async def list_downloads(
    status: Annotated[
        Literal["all", "downloading", "completed", "paused"],
        Field(description="Filter by download status"),
    ] = "all",
) -> list[dict]:
    status_filter = None if status == "all" else status
    torrents = await list_torrents(status_filter) or []
    return [
        {
            "name": t.get("name", ""),
            "size": t.get("size", 0),
            "progress": t.get("progress", 0),
            "state": t.get("state", ""),
            "dlspeed": t.get("dlspeed", 0),
            "upspeed": t.get("upspeed", 0),
            "eta": t.get("eta", 0),
            "downloader": t["downloader_id"],
        }
        for t in torrents
    ]


@mcp.tool(
    description="List all configured RSS feeds with their connection status and health information.",
    structured_output=False,
)
async def list_rss_feeds() -> list[dict]:
    async with Database() as db:
        feeds = await db.rss.search_all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "url": f.url,
            "aggregate": f.aggregate,
            "parser": f.parser,
            "enabled": f.enabled,
            "connection_status": f.connection_status,
            "last_checked_at": f.last_checked_at,
            "last_error": f.last_error,
        }
        for f in feeds
    ]


@mcp.tool(
    description="Get the current program status including version, running state, and first-run flag.",
    structured_output=False,
)
def get_program_status() -> dict:
    ctx = get_context()
    return {
        "version": VERSION,
        "running": ctx.is_running if ctx is not None else False,
        "first_run": ctx.first_run if ctx is not None else True,
    }


@mcp.tool(
    description="Trigger an immediate refresh of all RSS feeds to check for new episodes.",
    structured_output=False,
)
async def refresh_feeds() -> dict:
    async with DownloaderPool() as downloaders:
        async with Database() as db:
            engine = RSSEngine(db)
            await engine.refresh_rss(downloaders)
    return {"status": True, "message": "RSS feeds refreshed successfully"}


@mcp.tool(
    description="Update settings for a tracked anime (episode offset, season offset, filters, etc.).",
    structured_output=False,
)
async def update_anime(
    id: Annotated[int, Field(description="The anime/bangumi ID to update")],
    episode_offset: Annotated[
        int | None, Field(description="Episode number offset for renaming")
    ] = None,
    season_offset: Annotated[
        int | None, Field(description="Season number offset for renaming")
    ] = None,
    season: Annotated[int | None, Field(description="Season number")] = None,
    filter: Annotated[
        str | None, Field(description="Comma-separated filter patterns to exclude")
    ] = None,
) -> dict:
    async with Database() as db:
        manager = TorrentManager(db)
        existing = await db.bangumi.search_id(id)
        if not existing:
            return {"error": f"Anime with id {id} not found"}

        update_data = BangumiUpdate(**existing.model_dump())
        if episode_offset is not None:
            update_data.episode_offset = episode_offset
        if season_offset is not None:
            update_data.season_offset = season_offset
        if season is not None:
            update_data.season = season
        if filter is not None:
            update_data.filter = filter

        resp = await manager.update_rule(id, update_data)
    return {"status": resp.status, "message": resp.msg_en}
