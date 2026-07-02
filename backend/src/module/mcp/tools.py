import json
import logging

from mcp import types

from module.conf import VERSION
from module.database import Database
from module.downloader import DownloadClient
from module.manager import SeasonCollector, TorrentManager
from module.models import Bangumi, BangumiUpdate, RSSItem
from module.rss import RSSAnalyser, RSSEngine
from module.searcher import SearchTorrent

from .runtime import get_context

logger = logging.getLogger(__name__)

TOOLS = [
    types.Tool(
        name="list_anime",
        description="List all tracked anime subscriptions. Returns title, season, status, and episode offset for each.",
        inputSchema={
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "description": "If true, only return active (non-disabled) anime",
                    "default": False,
                },
            },
        },
    ),
    types.Tool(
        name="get_anime",
        description="Get detailed information about a specific anime subscription by its ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "The anime/bangumi ID",
                },
            },
            "required": ["id"],
        },
    ),
    types.Tool(
        name="search_anime",
        description="Search for anime torrents across torrent sites (Mikan, DMHY, Nyaa). Returns available anime matching the keywords.",
        inputSchema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search keywords (e.g. anime title)",
                },
                "site": {
                    "type": "string",
                    "description": "Torrent site to search",
                    "enum": ["mikan", "dmhy", "nyaa"],
                    "default": "mikan",
                },
            },
            "required": ["keywords"],
        },
    ),
    types.Tool(
        name="subscribe_anime",
        description="Subscribe to an anime series by providing its RSS link. Analyzes the RSS feed and sets up automatic downloading.",
        inputSchema={
            "type": "object",
            "properties": {
                "rss_link": {
                    "type": "string",
                    "description": "RSS feed URL for the anime (obtained from search_anime results)",
                },
                "parser": {
                    "type": "string",
                    "description": "RSS parser type",
                    "enum": ["mikan", "dmhy", "nyaa"],
                    "default": "mikan",
                },
            },
            "required": ["rss_link"],
        },
    ),
    types.Tool(
        name="unsubscribe_anime",
        description="Unsubscribe from an anime. Can either disable (keeps data) or fully delete the subscription.",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "The anime/bangumi ID to unsubscribe",
                },
                "delete": {
                    "type": "boolean",
                    "description": "If true, permanently delete the subscription. If false, just disable it.",
                    "default": False,
                },
            },
            "required": ["id"],
        },
    ),
    types.Tool(
        name="list_downloads",
        description="Show current torrent download status from the download client (qBittorrent/Aria2).",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by download status",
                    "enum": ["all", "downloading", "completed", "paused"],
                    "default": "all",
                },
            },
        },
    ),
    types.Tool(
        name="list_rss_feeds",
        description="List all configured RSS feeds with their connection status and health information.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="get_program_status",
        description="Get the current program status including version, running state, and first-run flag.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="refresh_feeds",
        description="Trigger an immediate refresh of all RSS feeds to check for new episodes.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="update_anime",
        description="Update settings for a tracked anime (episode offset, season offset, filters, etc.).",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "The anime/bangumi ID to update",
                },
                "episode_offset": {
                    "type": "integer",
                    "description": "Episode number offset for renaming",
                },
                "season_offset": {
                    "type": "integer",
                    "description": "Season number offset for renaming",
                },
                "season": {
                    "type": "integer",
                    "description": "Season number",
                },
                "filter": {
                    "type": "string",
                    "description": "Comma-separated filter patterns to exclude",
                },
            },
            "required": ["id"],
        },
    ),
]


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


async def handle_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        result = await _dispatch(name, arguments)
        return [
            types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))
        ]
    except Exception as e:
        logger.exception("[MCP] Tool %s failed", name)
        return [
            types.TextContent(
                type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False)
            )
        ]


async def _dispatch(name: str, args: dict) -> dict | list:
    if name == "list_anime":
        return await _list_anime(args.get("active_only", False))
    elif name == "get_anime":
        return await _get_anime(args["id"])
    elif name == "search_anime":
        return await _search_anime(args["keywords"], args.get("site", "mikan"))
    elif name == "subscribe_anime":
        return await _subscribe_anime(args["rss_link"], args.get("parser", "mikan"))
    elif name == "unsubscribe_anime":
        return await _unsubscribe_anime(args["id"], args.get("delete", False))
    elif name == "list_downloads":
        return await _list_downloads(args.get("status", "all"))
    elif name == "list_rss_feeds":
        return await _list_rss_feeds()
    elif name == "get_program_status":
        return _get_program_status()
    elif name == "refresh_feeds":
        return await _refresh_feeds()
    elif name == "update_anime":
        return await _update_anime(args)
    else:
        return {"error": f"Unknown tool: {name}"}


async def _list_anime(active_only: bool) -> list[dict]:
    async with Database() as db:
        manager = TorrentManager(db)
        if active_only:
            items = await manager.search_all_bangumi()
        else:
            items = await db.bangumi.search_all()
    return [_bangumi_to_dict(b) for b in items]


async def _get_anime(bangumi_id: int) -> dict:
    async with Database() as db:
        manager = TorrentManager(db)
        result = await manager.search_one(bangumi_id)
    if isinstance(result, Bangumi):
        return _bangumi_to_dict(result)
    return {"error": result.msg_en}


async def _search_anime(keywords: str, site: str) -> list[dict]:
    keyword_list = keywords.split()
    results = []
    st = SearchTorrent()
    async for item_json in st.analyse_keyword(keywords=keyword_list, site=site):
        results.append(json.loads(item_json))
        if len(results) >= 20:
            break
    return results


async def _subscribe_anime(rss_link: str, parser: str) -> dict:
    analyser = RSSAnalyser()
    rss = RSSItem(url=rss_link, parser=parser)
    data = await analyser.link_to_data(rss)
    if not isinstance(data, Bangumi):
        return {"error": data.msg_en if hasattr(data, "msg_en") else str(data)}
    resp = await SeasonCollector.subscribe_season(data, parser=parser)
    return {"status": resp.status, "message": resp.msg_en}


async def _unsubscribe_anime(bangumi_id: int, delete: bool) -> dict:
    async with Database() as db:
        manager = TorrentManager(db)
        if delete:
            resp = await manager.delete_rule(bangumi_id)
        else:
            resp = await manager.disable_rule(bangumi_id)
    return {"status": resp.status, "message": resp.msg_en}


async def _list_downloads(status: str) -> list[dict]:
    status_filter = None if status == "all" else status
    async with DownloadClient() as client:
        torrents = await client.get_torrent_info(
            status_filter=status_filter, category="Bangumi"
        )
    return [
        {
            "name": t.get("name", ""),
            "size": t.get("size", 0),
            "progress": t.get("progress", 0),
            "state": t.get("state", ""),
            "dlspeed": t.get("dlspeed", 0),
            "upspeed": t.get("upspeed", 0),
            "eta": t.get("eta", 0),
        }
        for t in torrents
    ]


async def _list_rss_feeds() -> list[dict]:
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


def _get_program_status() -> dict:
    ctx = get_context()
    return {
        "version": VERSION,
        "running": ctx.is_running if ctx is not None else False,
        "first_run": ctx.first_run if ctx is not None else True,
    }


async def _refresh_feeds() -> dict:
    async with DownloadClient() as client:
        async with Database() as db:
            engine = RSSEngine(db)
            await engine.refresh_rss(client)
    return {"status": True, "message": "RSS feeds refreshed successfully"}


async def _update_anime(args: dict) -> dict:
    bangumi_id = args["id"]
    async with Database() as db:
        manager = TorrentManager(db)
        existing = await db.bangumi.search_id(bangumi_id)
        if not existing:
            return {"error": f"Anime with id {bangumi_id} not found"}

        update_data = BangumiUpdate(**existing.model_dump())
        if "episode_offset" in args:
            update_data.episode_offset = args["episode_offset"]
        if "season_offset" in args:
            update_data.season_offset = args["season_offset"]
        if "season" in args:
            update_data.season = args["season"]
        if "filter" in args:
            update_data.filter = args["filter"]

        resp = await manager.update_rule(bangumi_id, update_data)
    return {"status": resp.status, "message": resp.msg_en}
