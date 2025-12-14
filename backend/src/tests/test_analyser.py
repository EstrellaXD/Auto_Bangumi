"""
Tests for RSS analyser.
Based on Goto_Bangumi/internal/refresh/analyser_test.go
"""

from unittest.mock import AsyncMock, patch

import pytest

from models import Bangumi, MikanInfo, RSSItem, TMDBInfo, Torrent
from module.rss.analyser import filter_torrent, torrent_to_bangumi


class TestFilterTorrent:
    """Tests for filter_torrent function.

    Based on TestFilter_torrent in analyser_test.go
    """

    @pytest.mark.parametrize(
        "torrent_name,exclude_filter,include_filter,expected",
        [
            # exclude_false: torrent contains "1080p" which is in exclude filter
            (
                "[喵萌奶茶屋&LoliHouse] 败犬女主角也太多了！ / 败犬女主太多了！ / 负けヒロインが多すぎる！ / Make Heroine ga Oosugiru! [01-12合集][WebRip 1080p HEVC-10bit AAC][简繁日内封字幕][Fin]",
                "1080p,meow",
                "",
                False,
            ),
            # exclude_true: torrent has 720p, not in exclude filter
            (
                "[喵萌奶茶屋&LoliHouse] 败犬女主角也太多了！ / 败犬女主太多了！ / 负けヒロインが多すぎる！ / Make Heroine ga Oosugiru! [01-12合集][WebRip 720p HEVC-10bit AAC][简繁日内封字幕][Fin]",
                "1080p,meow",
                "",
                True,
            ),
            # include_true: torrent contains "1080p" which is in include filter
            (
                "[喵萌奶茶屋&LoliHouse] 败犬女主角也太多了！ / 败犬女主太多了！ / 负けヒロインが多すぎる！ / Make Heroine ga Oosugiru! [01-12合集][WebRip 1080p HEVC-10bit AAC][简繁日内封字幕][Fin]",
                "",
                "1080p,meow",
                True,
            ),
            # include_false: torrent has 720p, not in include filter "1080p,meow"
            (
                "[喵萌奶茶屋&LoliHouse] 败犬女主角也太多了！ / 败犬女主太多了！ / 负けヒロインが多すぎる！ / Make Heroine ga Oosugiru! [01-12合集][WebRip 720p HEVC-10bit AAC][简繁日内封字幕][Fin]",
                "",
                "1080p,meow",
                False,
            ),
            # include_empty: no filter, should pass
            (
                "[喵萌奶茶屋&LoliHouse] 败犬女主角也太多了！ / 败犬女主太多了！ / 负けヒロインが多すぎる！ / Make Heroine ga Oosugiru! [01-12合集][WebRip 720p HEVC-10bit AAC][简繁日内封字幕][Fin]",
                "",
                "",
                True,
            ),
        ],
        ids=["exclude_false", "exclude_true", "include_true", "include_false", "include_empty"],
    )
    def test_filter_torrent(self, torrent_name, exclude_filter, include_filter, expected):
        torrent = Torrent(url="test", name=torrent_name)
        bangumi = Bangumi(
            official_title="Test",
            exclude_filter=exclude_filter,
            include_filter=include_filter,
        )

        result = filter_torrent(torrent, bangumi)

        assert result == expected, f"filter_torrent() = {result}, want {expected}"


class TestTorrentToBangumi:
    """Tests for torrent_to_bangumi function.

    Based on TestTorrentToBangumi in analyser_test.go
    Uses mock to avoid network requests.
    """

    @pytest.mark.asyncio
    async def test_with_mikan_and_tmdb(self):
        """Test torrent_to_bangumi with both mikan and tmdb parser."""
        torrent = Torrent(
            url="magnet:?xt=urn:btih:EXAMPLE1",
            name="[ANi] Chitose Is in the Ramune Bottle / 弹珠汽水瓶里的千岁同学 - 02 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]",
            homepage="https://mikanani.me/Home/Episode/7c8c41e409922d9f2c34a726c92e77daf05558ff",
        )
        rss = RSSItem(
            url="https://mikanani.me/RSS/Search?searchstr=ANI",
            name="Test RSS",
            parser="mikan",
        )

        mock_mikan_info = MikanInfo(
            id="3774#123",
            official_title="弹珠汽水瓶里的千岁同学",
            season=1,
            poster_link="https://mikanani.me/images/Bangumi/202510/37749647.jpg",
        )

        mock_tmdb_info = TMDBInfo(
            id=261343,
            title="弹珠汽水瓶里的千岁同学",
            original_title="千歳くんはラムネ瓶のなか",
            year="2025",
            season=1,
            poster_link="https://image.tmdb.org/t/p/w780/poster.jpg",
        )

        with (
            patch("module.rss.analyser.MikanParser") as mock_mikan_cls,
            patch("module.rss.analyser.tmdb_parser", new_callable=AsyncMock) as mock_tmdb,
        ):
            mock_mikan_instance = mock_mikan_cls.return_value
            mock_mikan_instance.parser = AsyncMock(return_value=mock_mikan_info)
            mock_tmdb.return_value = mock_tmdb_info

            bangumi = await torrent_to_bangumi(torrent, rss)

            assert bangumi is not None
            assert bangumi.official_title == "弹珠汽水瓶里的千岁同学"
            assert bangumi.rss_link == "https://mikanani.me/RSS/Search?searchstr=ANI"
            assert bangumi.season == 1
            assert bangumi.year == "2025"
            assert bangumi.mikan_id == "3774#123"
            assert bangumi.tmdb_id == "261343"

    @pytest.mark.asyncio
    async def test_without_homepage(self):
        """Test torrent_to_bangumi without homepage (no mikan parsing)."""
        torrent = Torrent(
            url="magnet:?xt=urn:btih:EXAMPLE2",
            name="[喵萌奶茶屋] 败犬女主太多了！ / Make Heroine ga Oosugiru! - 01 [1080p][简繁日内封字幕]",
            homepage=None,
        )
        rss = RSSItem(
            url="https://mikanani.me/RSS/Search?searchstr=test",
            name="Test RSS",
            parser="mikan",
        )

        mock_tmdb_info = TMDBInfo(
            id=12345,
            title="败犬女主太多了",
            original_title="負けヒロインが多すぎる！",
            year="2024",
            season=1,
            poster_link="https://image.tmdb.org/t/p/w780/loser.jpg",
        )

        with patch("module.rss.analyser.tmdb_parser", new_callable=AsyncMock) as mock_tmdb:
            mock_tmdb.return_value = mock_tmdb_info

            bangumi = await torrent_to_bangumi(torrent, rss)

            assert bangumi is not None
            assert bangumi.official_title == "败犬女主太多了"
            assert bangumi.rss_link == "https://mikanani.me/RSS/Search?searchstr=test"
            assert bangumi.tmdb_id == "12345"
            assert bangumi.mikan_id is None

    @pytest.mark.asyncio
    async def test_tmdb_not_found_uses_raw_parser(self):
        """Test torrent_to_bangumi uses RawParser result when TMDB returns None."""
        torrent = Torrent(
            url="magnet:?xt=urn:btih:EXAMPLE3",
            name="[字幕组] 未知动漫 - 01 [1080p]",
            homepage=None,
        )
        rss = RSSItem(url="https://example.com/rss", name="Test", parser="mikan")

        with patch("module.rss.analyser.tmdb_parser", new_callable=AsyncMock) as mock_tmdb:
            mock_tmdb.return_value = None

            bangumi = await torrent_to_bangumi(torrent, rss)

            # When TMDB returns None, uses RawParser result
            assert bangumi is not None
            assert bangumi.rss_link == "https://example.com/rss"
            assert bangumi.tmdb_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
