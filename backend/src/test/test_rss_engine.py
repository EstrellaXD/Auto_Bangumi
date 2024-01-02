import pytest
from module.rss.engine import RSSEngine

from .test_database import engine as e


@pytest.mark.asyncio
async def test_rss_engine():
    with RSSEngine(e) as engine:
        rss_link = "https://mikanani.me/RSS/Bangumi?bangumiId=2353&subgroupid=552"

        resp = await engine.add_rss(rss_link, aggregate=False)
        assert resp.status

        result = engine.rss.search_active()
        assert result[1].name == "Mikan Project - 无职转生～到了异世界就拿出真本事～"

        new_torrents = await engine.pull_rss(result[1])
        torrent = new_torrents[0]
        assert torrent.name == "[Lilith-Raws] 无职转生，到了异世界就拿出真本事 / Mushoku Tensei - 11 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
