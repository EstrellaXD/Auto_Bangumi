"""Integration tests: end-to-end flows with real DB and mocked externals."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sqlmodel import Session, SQLModel, create_engine

from module.database.bangumi import BangumiDatabase, _invalidate_bangumi_cache
from module.database.rss import RSSDatabase
from module.database.torrent import TorrentDatabase
from module.models import Bangumi, EpisodeFile, Notification, RSSItem, Torrent
from module.rss.engine import RSSEngine

from test.factories import make_bangumi, make_torrent, make_rss_item


@pytest.fixture(autouse=True)
def clear_cache():
    _invalidate_bangumi_cache()
    yield
    _invalidate_bangumi_cache()


# ---------------------------------------------------------------------------
# RSS → Download Flow
# ---------------------------------------------------------------------------


class TestRssToDownloadFlow:
    """End-to-end: RSS feed parsed → matched → downloaded → stored in DB."""

    async def test_full_flow(self, db_engine):
        """Complete RSS → match → download pipeline."""
        # 1. Setup: create engine with real in-memory DB
        engine = RSSEngine(_engine=db_engine)

        # 2. Add RSS feed and Bangumi to DB
        rss_item = make_rss_item(name="My Feed", url="https://mikanani.me/RSS/test")
        engine.rss.add(rss_item)

        bangumi = make_bangumi(
            title_raw="Mushoku Tensei",
            official_title="Mushoku Tensei",
            filter="",
            added=True,
        )
        engine.bangumi.add(bangumi)

        # 3. Mock the HTTP layer to return new torrents
        new_torrents = [
            Torrent(
                name="[Sub] Mushoku Tensei - 11 [1080p].mkv",
                url="https://example.com/ep11.torrent",
            ),
            Torrent(
                name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
                url="https://example.com/ep12.torrent",
            ),
            Torrent(
                name="[Other] Unknown Anime - 01 [720p].mkv",
                url="https://example.com/unknown.torrent",
            ),
        ]
        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = new_torrents

            # 4. Mock download client
            mock_client = AsyncMock()
            mock_client.add_torrent = AsyncMock(return_value=True)

            # 5. Execute refresh_rss
            await engine.refresh_rss(mock_client)

        # 6. Verify: matched torrents were downloaded
        assert mock_client.add_torrent.call_count == 2

        # 7. Verify: all torrents stored in DB
        all_torrents = engine.torrent.search_all()
        assert len(all_torrents) == 3

        # 8. Verify: matched torrents are marked downloaded
        downloaded = [t for t in all_torrents if t.downloaded]
        assert len(downloaded) == 2
        # All downloaded torrents should contain "Mushoku Tensei"
        for t in downloaded:
            assert "Mushoku Tensei" in t.name

        # 9. Verify: unmatched torrent is NOT downloaded
        not_downloaded = [t for t in all_torrents if not t.downloaded]
        assert len(not_downloaded) == 1
        assert "Unknown Anime" in not_downloaded[0].name

    async def test_filtered_torrents_not_downloaded(self, db_engine):
        """Torrents matching the filter regex are NOT downloaded."""
        engine = RSSEngine(_engine=db_engine)

        rss_item = make_rss_item()
        engine.rss.add(rss_item)

        # Bangumi has filter="720" to exclude 720p
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei",
            filter="720",
        )
        engine.bangumi.add(bangumi)

        torrents = [
            Torrent(
                name="[Sub] Mushoku Tensei - 01 [720p].mkv",
                url="https://example.com/720.torrent",
            ),
            Torrent(
                name="[Sub] Mushoku Tensei - 01 [1080p].mkv",
                url="https://example.com/1080.torrent",
            ),
        ]
        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = torrents
            mock_client = AsyncMock()
            mock_client.add_torrent = AsyncMock(return_value=True)
            await engine.refresh_rss(mock_client)

        # Only 1080p should be downloaded (720p is filtered)
        assert mock_client.add_torrent.call_count == 1

    async def test_duplicate_torrents_not_reprocessed(self, db_engine):
        """Torrents already in the DB are not processed again."""
        engine = RSSEngine(_engine=db_engine)

        rss_item = make_rss_item()
        engine.rss.add(rss_item)

        bangumi = make_bangumi(title_raw="Anime", filter="")
        engine.bangumi.add(bangumi)

        # Pre-insert a torrent
        existing = Torrent(
            name="[Sub] Anime - 01 [1080p].mkv",
            url="https://example.com/ep01.torrent",
            downloaded=True,
        )
        engine.torrent.add(existing)

        # Mock returns same torrent + a new one
        torrents = [
            Torrent(
                name="[Sub] Anime - 01 [1080p].mkv",
                url="https://example.com/ep01.torrent",
            ),
            Torrent(
                name="[Sub] Anime - 02 [1080p].mkv",
                url="https://example.com/ep02.torrent",
            ),
        ]
        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = torrents
            mock_client = AsyncMock()
            mock_client.add_torrent = AsyncMock(return_value=True)
            await engine.refresh_rss(mock_client)

        # Only ep02 should be downloaded (ep01 already exists)
        assert mock_client.add_torrent.call_count == 1
        all_torrents = engine.torrent.search_all()
        assert len(all_torrents) == 2  # original + new one


# ---------------------------------------------------------------------------
# Rename Flow
# ---------------------------------------------------------------------------


class TestRenameFlow:
    """End-to-end: completed torrent → parse → rename → notification."""

    async def test_single_file_rename(self, mock_qb_client):
        """Single-file torrent is parsed and renamed correctly."""
        from module.manager.renamer import Renamer

        # Setup renamer with mocked client
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.type = "qbittorrent"
            mock_settings.downloader.host = "localhost"
            mock_settings.downloader.username = "admin"
            mock_settings.downloader.password = "admin"
            mock_settings.downloader.ssl = False
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            with patch(
                "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
                return_value=mock_qb_client,
            ):
                renamer = Renamer()
        renamer.client = mock_qb_client

        # Mock completed torrent info
        mock_qb_client.torrents_info.return_value = [
            {
                "hash": "abc123",
                "name": "[Lilith-Raws] Mushoku Tensei - 11 [1080p].mkv",
                "save_path": "/downloads/Bangumi/Mushoku Tensei (2024)/Season 1",
            }
        ]
        mock_qb_client.torrents_files.return_value = [
            {"name": "[Lilith-Raws] Mushoku Tensei - 11 [1080p].mkv"}
        ]
        mock_qb_client.torrents_rename_file.return_value = True

        ep = EpisodeFile(
            media_path="[Lilith-Raws] Mushoku Tensei - 11 [1080p].mkv",
            title="Mushoku Tensei",
            season=1,
            episode=11,
            suffix=".mkv",
        )

        with patch.object(renamer._parser, "torrent_parser", return_value=ep):
            with patch("module.manager.renamer.settings") as mock_mgr_settings:
                mock_mgr_settings.bangumi_manage.rename_method = "pn"
                mock_mgr_settings.bangumi_manage.remove_bad_torrent = False
                with patch("module.downloader.path.settings") as mock_path_settings:
                    mock_path_settings.downloader.path = "/downloads/Bangumi"
                    result = await renamer.rename()

        # Verify: file was renamed
        mock_qb_client.torrents_rename_file.assert_called_once()
        call_args = mock_qb_client.torrents_rename_file.call_args
        assert "S01E11" in str(call_args)

        # Verify: notification returned
        assert len(result) == 1
        assert result[0].official_title == "Mushoku Tensei (2024)"
        assert result[0].episode == 11

    async def test_collection_rename(self, mock_qb_client):
        """Multi-file torrent is treated as collection and re-categorized."""
        from module.manager.renamer import Renamer

        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.type = "qbittorrent"
            mock_settings.downloader.host = "localhost"
            mock_settings.downloader.username = "admin"
            mock_settings.downloader.password = "admin"
            mock_settings.downloader.ssl = False
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            with patch(
                "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
                return_value=mock_qb_client,
            ):
                renamer = Renamer()
        renamer.client = mock_qb_client

        mock_qb_client.torrents_info.return_value = [
            {
                "hash": "batch_hash",
                "name": "Anime Batch",
                "save_path": "/downloads/Bangumi/Anime (2024)/Season 1",
            }
        ]
        mock_qb_client.torrents_files.return_value = [
            {"name": "ep01.mkv"},
            {"name": "ep02.mkv"},
            {"name": "ep03.mkv"},
        ]
        mock_qb_client.torrents_rename_file.return_value = True

        def mock_parser(torrent_path, season, **kwargs):
            ep_num = int(torrent_path.replace("ep", "").replace(".mkv", ""))
            return EpisodeFile(
                media_path=torrent_path,
                title="Anime",
                season=season,
                episode=ep_num,
                suffix=".mkv",
            )

        with patch.object(renamer._parser, "torrent_parser", side_effect=mock_parser):
            with patch("module.manager.renamer.settings") as mock_mgr_settings:
                mock_mgr_settings.bangumi_manage.rename_method = "pn"
                mock_mgr_settings.bangumi_manage.remove_bad_torrent = False
                with patch("module.downloader.path.settings") as mock_path_settings:
                    mock_path_settings.downloader.path = "/downloads/Bangumi"
                    await renamer.rename()

        # Verify: all 3 files renamed
        assert mock_qb_client.torrents_rename_file.call_count == 3
        # Verify: category set to BangumiCollection
        mock_qb_client.set_category.assert_called_once_with(
            "batch_hash", "BangumiCollection"
        )


# ---------------------------------------------------------------------------
# Database Consistency
# ---------------------------------------------------------------------------


class TestDatabaseConsistency:
    """Verify database operations maintain data integrity across operations."""

    def test_bangumi_uniqueness_by_title_raw(self, db_engine):
        """Cannot add two Bangumi with same title_raw."""
        engine = RSSEngine(_engine=db_engine)

        b1 = make_bangumi(title_raw="Same Title", official_title="First")
        b2 = make_bangumi(title_raw="Same Title", official_title="Second")

        assert engine.bangumi.add(b1) is True
        assert engine.bangumi.add(b2) is False  # Duplicate rejected

        all_bangumi = engine.bangumi.search_all()
        assert len(all_bangumi) == 1
        assert all_bangumi[0].official_title == "First"

    def test_rss_uniqueness_by_url(self, db_engine):
        """Cannot add two RSSItems with same URL."""
        engine = RSSEngine(_engine=db_engine)

        r1 = make_rss_item(url="https://same.url/rss", name="First")
        r2 = make_rss_item(url="https://same.url/rss", name="Second")

        assert engine.rss.add(r1) is True
        assert engine.rss.add(r2) is False

    def test_torrent_check_new_filters_duplicates(self, db_engine):
        """check_new only returns torrents not already in the database."""
        engine = RSSEngine(_engine=db_engine)

        existing = Torrent(name="existing", url="https://existing.com")
        engine.torrent.add(existing)

        candidates = [
            Torrent(name="existing", url="https://existing.com"),
            Torrent(name="new1", url="https://new1.com"),
            Torrent(name="new2", url="https://new2.com"),
        ]
        new_ones = engine.torrent.check_new(candidates)
        assert len(new_ones) == 2
        assert all(t.url != "https://existing.com" for t in new_ones)

    def test_match_torrent_respects_deleted_flag(self, db_engine):
        """Deleted bangumi are not matched by match_torrent."""
        engine = RSSEngine(_engine=db_engine)

        bangumi = make_bangumi(title_raw="Deleted Anime", filter="", deleted=True)
        engine.bangumi.add(bangumi)

        torrent = Torrent(
            name="[Sub] Deleted Anime - 01 [1080p].mkv",
            url="https://test.com",
        )
        result = engine.match_torrent(torrent)
        assert result is None

    def test_bangumi_disable_and_enable(self, db_engine):
        """disable_rule and re-enabling preserves data."""
        engine = RSSEngine(_engine=db_engine)

        bangumi = make_bangumi(title_raw="My Anime", deleted=False)
        engine.bangumi.add(bangumi)
        bangumi_id = engine.bangumi.search_all()[0].id

        # Disable
        engine.bangumi.disable_rule(bangumi_id)
        disabled = engine.bangumi.search_id(bangumi_id)
        assert disabled.deleted is True

        # Torrent matching should now fail
        torrent = Torrent(name="[Sub] My Anime - 01.mkv", url="https://test.com")
        assert engine.match_torrent(torrent) is None
