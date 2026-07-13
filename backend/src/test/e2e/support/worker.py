"""Offline fixture worker for runtime E2E tests.

This process changes into the sandbox before importing any production module,
so the normal relative config and SQLite paths resolve inside that sandbox.
It never runs concurrently with the backend process.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

_BANGUMI_DEFAULTS: dict[str, Any] = {
    "official_title": "Fixture Anime",
    "year": "2026",
    "title_raw": "Fixture Anime",
    "season": 1,
    "season_raw": None,
    "group_name": "E2E",
    "dpi": "1080P",
    "source": "WebRip",
    "subtitle": "CHS",
    "eps_collect": False,
    "episode_offset": 0,
    "season_offset": 0,
    "filter": "",
    "rss_link": "",
    "poster_link": None,
    "added": True,
    "rule_name": None,
    "save_path": None,
    "deleted": False,
    "archived": False,
    "air_weekday": None,
    "weekday_locked": False,
    "needs_review": False,
    "needs_review_reason": None,
    "suggested_season_offset": None,
    "suggested_episode_offset": None,
    "title_aliases": None,
    "preferred_group": None,
    "preferred_resolution": None,
    "episode_type": "episode",
}


async def _seed(payload_path: Path) -> dict[str, Any]:
    from module.database import Database
    from module.models import Bangumi, RSSItem, Torrent

    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    bangumi_rows = [
        Bangumi(**(_BANGUMI_DEFAULTS | item)) for item in payload.get("bangumi", [])
    ]
    rss_rows = [RSSItem(**item) for item in payload.get("rss", [])]
    torrent_rows = [Torrent(**item) for item in payload.get("torrents", [])]

    async with Database() as db:
        for bangumi in bangumi_rows:
            db.add(bangumi)
        await db.commit()
        for rss in rss_rows:
            db.add(rss)
        for torrent in torrent_rows:
            db.add(torrent)
        await db.commit()

    return {
        "seeded": True,
        "bangumi": len(bangumi_rows),
        "rss": len(rss_rows),
        "torrents": len(torrent_rows),
    }


async def _offset(bangumi_id: int) -> dict[str, Any]:
    from module.core.offset_scanner import OffsetScanner

    flagged = await OffsetScanner().check_single(bangumi_id)
    return {"flagged": flagged, "bangumi_id": bangumi_id}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "offset"))
    parser.add_argument("work_dir", type=Path)
    parser.add_argument("argument")
    args = parser.parse_args()

    work_dir = args.work_dir.resolve()
    os.chdir(work_dir)
    if args.command == "seed":
        result = asyncio.run(_seed(Path(args.argument).resolve()))
    else:
        result = asyncio.run(_offset(int(args.argument)))
    print(f"E2E_RESULT={json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
