"""内置 MCP 资源：静态资源与 ``autobangumi://anime/{id}`` 模板，内容均为 JSON 文本。

插件提供的资源（``autobangumi://plugins/<plugin-id>/<id>``）由
``AutoBangumiMCP.read_resource`` 分发。
"""

import json

from module.database import Database
from module.manager import TorrentManager
from module.models import Bangumi

from .server import mcp
from .tools import _bangumi_to_dict, get_program_status

JSON = "application/json"


@mcp.resource(
    "autobangumi://anime/list",
    name="All tracked anime",
    description="List of all anime subscriptions being tracked by AutoBangumi",
    mime_type=JSON,
)
async def anime_list() -> str:
    async with Database() as db:
        items = await db.bangumi.search_all()
    return json.dumps([_bangumi_to_dict(b) for b in items], ensure_ascii=False)


@mcp.resource(
    "autobangumi://status",
    name="Program status",
    description="Current AutoBangumi program status, version, and state",
    mime_type=JSON,
)
def program_status() -> str:
    return json.dumps(get_program_status())


@mcp.resource(
    "autobangumi://rss/feeds",
    name="RSS feeds",
    description="All configured RSS feeds with health status",
    mime_type=JSON,
)
async def rss_feeds() -> str:
    async with Database() as db:
        feeds = await db.rss.search_all()
    return json.dumps(
        [
            {
                "id": f.id,
                "name": f.name,
                "url": f.url,
                "enabled": f.enabled,
                "connection_status": f.connection_status,
                "last_checked_at": f.last_checked_at,
            }
            for f in feeds
        ],
        ensure_ascii=False,
    )


@mcp.resource(
    "autobangumi://anime/{id}",
    name="Anime details",
    description="Detailed information about a specific tracked anime by ID",
    mime_type=JSON,
)
async def anime_detail(id: str) -> str:
    try:
        anime_id = int(id)
    except ValueError:
        return json.dumps({"error": f"Invalid anime ID: {id}"})
    async with Database() as db:
        manager = TorrentManager(db)
        result = await manager.search_one(anime_id)
    if isinstance(result, Bangumi):
        return json.dumps(_bangumi_to_dict(result), ensure_ascii=False)
    return json.dumps({"error": result.msg_en})
