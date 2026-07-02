"""MCP resource definitions and handlers for AutoBangumi.

``RESOURCES`` lists static resources; ``RESOURCE_TEMPLATES`` lists URI
templates for parameterised lookups. ``handle_resource`` resolves a URI
to its JSON payload.
"""

import json
import logging

from mcp import types

from module.conf import VERSION
from module.database import Database
from module.manager import TorrentManager
from module.models import Bangumi
from module.rss import RSSEngine

from .tools import _bangumi_to_dict

logger = logging.getLogger(__name__)

RESOURCES = [
    types.Resource(
        uri="autobangumi://anime/list",
        name="All tracked anime",
        description="List of all anime subscriptions being tracked by AutoBangumi",
        mimeType="application/json",
    ),
    types.Resource(
        uri="autobangumi://status",
        name="Program status",
        description="Current AutoBangumi program status, version, and state",
        mimeType="application/json",
    ),
    types.Resource(
        uri="autobangumi://rss/feeds",
        name="RSS feeds",
        description="All configured RSS feeds with health status",
        mimeType="application/json",
    ),
]

RESOURCE_TEMPLATES = [
    types.ResourceTemplate(
        uriTemplate="autobangumi://anime/{id}",
        name="Anime details",
        description="Detailed information about a specific tracked anime by ID",
        mimeType="application/json",
    ),
]


def handle_resource(uri: str) -> str:
    """Return a JSON string for the given MCP resource URI.

    Supported URIs:
    - ``autobangumi://anime/list`` - all tracked anime
    - ``autobangumi://status`` - program version and running state
    - ``autobangumi://rss/feeds`` - configured RSS feeds
    - ``autobangumi://anime/{id}`` - single anime by integer ID
    """
    if uri == "autobangumi://anime/list":
        with Database() as db:
            manager = TorrentManager(db)
            items = manager.bangumi.search_all()
        return json.dumps([_bangumi_to_dict(b) for b in items], ensure_ascii=False)

    elif uri == "autobangumi://status":
        from module.api.program import program

        return json.dumps(
            {
                "version": VERSION,
                "running": program.is_running,
                "first_run": program.first_run,
            }
        )

    elif uri == "autobangumi://rss/feeds":
        with Database() as db:
            engine = RSSEngine(db)
            feeds = engine.rss.search_all()
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

    elif uri.startswith("autobangumi://anime/"):
        anime_id = uri.split("/")[-1]
        try:
            anime_id = int(anime_id)
        except ValueError:
            return json.dumps({"error": f"Invalid anime ID: {anime_id}"})
        with Database() as db:
            manager = TorrentManager(db)
            result = manager.search_one(anime_id)
        if isinstance(result, Bangumi):
            return json.dumps(_bangumi_to_dict(result), ensure_ascii=False)
        return json.dumps({"error": result.msg_en})

    return json.dumps({"error": f"Unknown resource: {uri}"})
