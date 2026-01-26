"""Tests for Renamer: gen_path, rename_file, rename_collection, rename flow."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from module.models import EpisodeFile, Notification, SubtitleFile
from module.manager.renamer import Renamer


# ---------------------------------------------------------------------------
# gen_path
# ---------------------------------------------------------------------------


class TestGenPath:
    def test_pn_method(self):
        """pn method: {title} S{ss}E{ee}{suffix}"""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=5, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi Name", method="pn")
        assert result == "My Anime S01E05.mkv"

    def test_advance_method(self):
        """advance method: {bangumi_name} S{ss}E{ee}{suffix}"""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=2, episode=12, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi Name", method="advance")
        assert result == "Bangumi Name S02E12.mkv"

    def test_none_method(self):
        """none method: returns original media_path unchanged."""
        ep = EpisodeFile(
            media_path="original/path/file.mkv",
            title="Test",
            season=1,
            episode=1,
            suffix=".mkv",
        )
        result = Renamer.gen_path(ep, "Bangumi", method="none")
        assert result == "original/path/file.mkv"

    def test_subtitle_none_method(self):
        """subtitle_none: returns original path unchanged."""
        sub = SubtitleFile(
            media_path="sub.ass",
            title="Test",
            season=1,
            episode=1,
            language="zh",
            suffix=".ass",
        )
        result = Renamer.gen_path(sub, "Bangumi", method="subtitle_none")
        assert result == "sub.ass"

    def test_subtitle_pn_method(self):
        """subtitle_pn: {title} S{ss}E{ee}.{language}{suffix}"""
        sub = SubtitleFile(
            media_path="sub.ass",
            title="My Anime",
            season=1,
            episode=3,
            language="zh",
            suffix=".ass",
        )
        result = Renamer.gen_path(sub, "Bangumi", method="subtitle_pn")
        assert result == "My Anime S01E03.zh.ass"

    def test_subtitle_advance_method(self):
        """subtitle_advance: {bangumi_name} S{ss}E{ee}.{language}{suffix}"""
        sub = SubtitleFile(
            media_path="sub.srt",
            title="My Anime",
            season=2,
            episode=7,
            language="zh-tw",
            suffix=".srt",
        )
        result = Renamer.gen_path(sub, "Bangumi Name", method="subtitle_advance")
        assert result == "Bangumi Name S02E07.zh-tw.srt"

    def test_zero_padding_single_digit(self):
        """Season and episode < 10 get zero-padded."""
        ep = EpisodeFile(
            media_path="old.mkv", title="Test", season=1, episode=9, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Test", method="pn")
        assert "S01E09" in result

    def test_no_padding_double_digit(self):
        """Season and episode >= 10 are NOT zero-padded."""
        ep = EpisodeFile(
            media_path="old.mkv", title="Test", season=10, episode=12, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Test", method="pn")
        assert "S10E12" in result

    def test_unknown_method_returns_original(self):
        """Unknown method returns original media_path."""
        ep = EpisodeFile(
            media_path="original.mkv", title="Test", season=1, episode=1, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Test", method="invalid_method")
        assert result == "original.mkv"

    def test_mp4_suffix(self):
        """Works with .mp4 suffix too."""
        ep = EpisodeFile(
            media_path="old.mp4", title="Test", season=1, episode=1, suffix=".mp4"
        )
        result = Renamer.gen_path(ep, "Test", method="pn")
        assert result.endswith(".mp4")


# ---------------------------------------------------------------------------
# rename_file
# ---------------------------------------------------------------------------


class TestRenameFile:
    @pytest.fixture
    def renamer(self, mock_qb_client):
        """Create Renamer with mocked internals."""
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.type = "qbittorrent"
            mock_settings.downloader.host = "localhost:8080"
            mock_settings.downloader.username = "admin"
            mock_settings.downloader.password = "admin"
            mock_settings.downloader.ssl = False
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            mock_settings.bangumi_manage.remove_bad_torrent = False
            mock_settings.bangumi_manage.rename_method = "pn"
            with patch(
                "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
                return_value=mock_qb_client,
            ):
                r = Renamer()
        r.client = mock_qb_client
        return r

    async def test_successful_rename(self, renamer):
        """rename_file parses, generates new path, renames, returns Notification."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=5, suffix=".mkv"
        )
        with patch.object(renamer._parser, "torrent_parser", return_value=ep):
            renamer.client.torrents_rename_file.return_value = True
            result = await renamer.rename_file(
                torrent_name="[Sub] My Anime - 05.mkv",
                media_path="old.mkv",
                bangumi_name="My Anime",
                method="pn",
                season=1,
                _hash="hash123",
            )

        assert result is not None
        assert isinstance(result, Notification)
        assert result.official_title == "My Anime"
        assert result.season == 1
        assert result.episode == 5

    async def test_parse_fails_no_remove(self, renamer):
        """When parser returns None and remove_bad_torrent=False, returns None."""
        with patch.object(renamer._parser, "torrent_parser", return_value=None):
            with patch("module.manager.renamer.settings") as mock_settings:
                mock_settings.bangumi_manage.remove_bad_torrent = False
                result = await renamer.rename_file(
                    torrent_name="garbage",
                    media_path="bad.mkv",
                    bangumi_name="Test",
                    method="pn",
                    season=1,
                    _hash="hash123",
                )

        assert result is None
        renamer.client.torrents_delete.assert_not_called()

    async def test_parse_fails_remove_bad(self, renamer):
        """When parser fails and remove_bad_torrent=True, deletes torrent."""
        with patch.object(renamer._parser, "torrent_parser", return_value=None):
            with patch("module.manager.renamer.settings") as mock_settings:
                mock_settings.bangumi_manage.remove_bad_torrent = True
                await renamer.rename_file(
                    torrent_name="garbage",
                    media_path="bad.mkv",
                    bangumi_name="Test",
                    method="pn",
                    season=1,
                    _hash="hash_bad",
                )

        renamer.client.torrents_delete.assert_called_once_with(
            "hash_bad", delete_files=True
        )

    async def test_same_path_skipped(self, renamer):
        """When generated path equals current path, no rename occurs."""
        ep = EpisodeFile(
            media_path="My Anime S01E05.mkv",
            title="My Anime",
            season=1,
            episode=5,
            suffix=".mkv",
        )
        with patch.object(renamer._parser, "torrent_parser", return_value=ep):
            result = await renamer.rename_file(
                torrent_name="test",
                media_path="My Anime S01E05.mkv",
                bangumi_name="My Anime",
                method="pn",
                season=1,
                _hash="hash123",
            )

        assert result is None
        renamer.client.torrents_rename_file.assert_not_called()

    async def test_duplicate_in_check_pool_skipped(self, renamer):
        """When new_path is already in check_pool, skip rename."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=5, suffix=".mkv"
        )
        # Pre-populate check_pool with the expected new path
        renamer.check_pool["My Anime S01E05.mkv"] = True

        with patch.object(renamer._parser, "torrent_parser", return_value=ep):
            result = await renamer.rename_file(
                torrent_name="test",
                media_path="old.mkv",
                bangumi_name="My Anime",
                method="pn",
                season=1,
                _hash="hash123",
            )

        assert result is None
        renamer.client.torrents_rename_file.assert_not_called()


# ---------------------------------------------------------------------------
# rename_collection
# ---------------------------------------------------------------------------


class TestRenameCollection:
    @pytest.fixture
    def renamer(self, mock_qb_client):
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.type = "qbittorrent"
            mock_settings.downloader.host = "localhost:8080"
            mock_settings.downloader.username = "admin"
            mock_settings.downloader.password = "admin"
            mock_settings.downloader.ssl = False
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            mock_settings.bangumi_manage.remove_bad_torrent = False
            with patch(
                "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
                return_value=mock_qb_client,
            ):
                r = Renamer()
        r.client = mock_qb_client
        return r

    async def test_renames_each_file(self, renamer):
        """rename_collection iterates media_list and renames each valid file."""
        media_list = ["ep01.mkv", "ep02.mkv", "ep03.mkv"]

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
            renamer.client.torrents_rename_file.return_value = True
            await renamer.rename_collection(
                media_list=media_list,
                bangumi_name="Anime",
                season=1,
                method="pn",
                _hash="hash123",
            )

        assert renamer.client.torrents_rename_file.call_count == 3

    async def test_skips_deep_files(self, renamer):
        """Files deeper than 2 levels are skipped (not is_ep)."""
        media_list = ["ep01.mkv", "extras/bonus/ep_sp.mkv"]

        ep = EpisodeFile(
            media_path="ep01.mkv",
            title="Anime",
            season=1,
            episode=1,
            suffix=".mkv",
        )
        with patch.object(renamer._parser, "torrent_parser", return_value=ep):
            renamer.client.torrents_rename_file.return_value = True
            await renamer.rename_collection(
                media_list=media_list,
                bangumi_name="Anime",
                season=1,
                method="pn",
                _hash="hash123",
            )

        # Only called once for ep01.mkv (depth 1)
        assert renamer.client.torrents_rename_file.call_count == 1


# ---------------------------------------------------------------------------
# rename_subtitles
# ---------------------------------------------------------------------------


class TestRenameSubtitles:
    @pytest.fixture
    def renamer(self, mock_qb_client):
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.type = "qbittorrent"
            mock_settings.downloader.host = "localhost:8080"
            mock_settings.downloader.username = "admin"
            mock_settings.downloader.password = "admin"
            mock_settings.downloader.ssl = False
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            with patch(
                "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
                return_value=mock_qb_client,
            ):
                r = Renamer()
        r.client = mock_qb_client
        return r

    async def test_renames_subtitles_with_language(self, renamer):
        """rename_subtitles prepends subtitle_ to method and renames files."""
        sub = SubtitleFile(
            media_path="sub.ass",
            title="Anime",
            season=1,
            episode=1,
            language="zh",
            suffix=".ass",
        )
        with patch.object(renamer._parser, "torrent_parser", return_value=sub):
            renamer.client.torrents_rename_file.return_value = True
            await renamer.rename_subtitles(
                subtitle_list=["sub.ass"],
                torrent_name="[Sub] Anime - 01.mkv",
                bangumi_name="Anime",
                season=1,
                method="pn",
                _hash="hash123",
            )

        renamer.client.torrents_rename_file.assert_called_once()
        call_args = renamer.client.torrents_rename_file.call_args
        new_path = call_args[1]["new_path"] if "new_path" in (call_args[1] or {}) else call_args[0][2]
        assert ".zh." in new_path


# ---------------------------------------------------------------------------
# rename (full flow)
# ---------------------------------------------------------------------------


class TestRenameFlow:
    @pytest.fixture
    def renamer(self, mock_qb_client):
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.type = "qbittorrent"
            mock_settings.downloader.host = "localhost:8080"
            mock_settings.downloader.username = "admin"
            mock_settings.downloader.password = "admin"
            mock_settings.downloader.ssl = False
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            mock_settings.bangumi_manage.remove_bad_torrent = False
            with patch(
                "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
                return_value=mock_qb_client,
            ):
                r = Renamer()
        r.client = mock_qb_client
        return r

    async def test_single_file_rename(self, renamer):
        """Full rename flow for a single-file torrent."""
        renamer.client.torrents_info.return_value = [
            {"hash": "h1", "name": "[Sub] Anime - 01.mkv", "save_path": "/downloads/Bangumi/Anime (2024)/Season 1"}
        ]
        renamer.client.torrents_files.return_value = [
            {"name": "[Sub] Anime - 01.mkv"}
        ]
        renamer.client.torrents_rename_file.return_value = True

        ep = EpisodeFile(
            media_path="[Sub] Anime - 01.mkv",
            title="Anime",
            season=1,
            episode=1,
            suffix=".mkv",
        )
        with patch.object(renamer._parser, "torrent_parser", return_value=ep):
            with patch("module.manager.renamer.settings") as mock_settings:
                mock_settings.bangumi_manage.rename_method = "pn"
                mock_settings.bangumi_manage.remove_bad_torrent = False
                with patch("module.downloader.path.settings") as mock_path_settings:
                    mock_path_settings.downloader.path = "/downloads/Bangumi"
                    result = await renamer.rename()

        assert len(result) == 1
        assert result[0].episode == 1

    async def test_collection_sets_category(self, renamer):
        """Multi-file torrent triggers collection rename and set_category."""
        renamer.client.torrents_info.return_value = [
            {"hash": "h1", "name": "Anime Collection", "save_path": "/downloads/Bangumi/Anime (2024)/Season 1"}
        ]
        renamer.client.torrents_files.return_value = [
            {"name": "ep01.mkv"},
            {"name": "ep02.mkv"},
            {"name": "ep03.mkv"},
        ]
        renamer.client.torrents_rename_file.return_value = True

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
            with patch("module.manager.renamer.settings") as mock_settings:
                mock_settings.bangumi_manage.rename_method = "pn"
                mock_settings.bangumi_manage.remove_bad_torrent = False
                with patch("module.downloader.path.settings") as mock_path_settings:
                    mock_path_settings.downloader.path = "/downloads/Bangumi"
                    await renamer.rename()

        renamer.client.set_category.assert_called_once_with("h1", "BangumiCollection")

    async def test_no_media_files_no_crash(self, renamer):
        """When torrent has no media files, logs warning but doesn't crash."""
        renamer.client.torrents_info.return_value = [
            {"hash": "h1", "name": "No Media", "save_path": "/downloads/Bangumi/Anime/Season 1"}
        ]
        renamer.client.torrents_files.return_value = [
            {"name": "readme.txt"},
            {"name": "info.nfo"},
        ]
        with patch("module.manager.renamer.settings") as mock_settings:
            mock_settings.bangumi_manage.rename_method = "pn"
            with patch("module.downloader.path.settings") as mock_path_settings:
                mock_path_settings.downloader.path = "/downloads/Bangumi"
                result = await renamer.rename()

        assert result == []
        renamer.client.torrents_rename_file.assert_not_called()


# ---------------------------------------------------------------------------
# _parse_bangumi_id_from_tags
# ---------------------------------------------------------------------------


class TestParseBangumiIdFromTags:
    """Tests for Renamer._parse_bangumi_id_from_tags static method."""

    def test_single_ab_tag(self):
        """Parses 'ab:123' format correctly."""
        result = Renamer._parse_bangumi_id_from_tags("ab:123")
        assert result == 123

    def test_ab_tag_with_other_tags(self):
        """Extracts ab tag from comma-separated list."""
        result = Renamer._parse_bangumi_id_from_tags("anime,ab:456,downloaded")
        assert result == 456

    def test_ab_tag_with_spaces(self):
        """Handles whitespace around tags."""
        result = Renamer._parse_bangumi_id_from_tags("  ab:789 , other_tag ")
        assert result == 789

    def test_empty_string(self):
        """Returns None for empty string."""
        result = Renamer._parse_bangumi_id_from_tags("")
        assert result is None

    def test_none_input(self):
        """Returns None for None input."""
        result = Renamer._parse_bangumi_id_from_tags(None)
        assert result is None

    def test_no_ab_tag(self):
        """Returns None when no ab: tag present."""
        result = Renamer._parse_bangumi_id_from_tags("anime,downloaded,HD")
        assert result is None

    def test_invalid_ab_tag_non_numeric(self):
        """Returns None when ab: tag has non-numeric value."""
        result = Renamer._parse_bangumi_id_from_tags("ab:not_a_number")
        assert result is None

    def test_ab_tag_first_match(self):
        """Returns first ab: tag if multiple present."""
        result = Renamer._parse_bangumi_id_from_tags("ab:111,ab:222")
        assert result == 111

    def test_ab_tag_zero(self):
        """Handles ab:0 correctly."""
        result = Renamer._parse_bangumi_id_from_tags("ab:0")
        assert result == 0

    def test_ab_tag_large_number(self):
        """Handles large bangumi IDs."""
        result = Renamer._parse_bangumi_id_from_tags("ab:999999")
        assert result == 999999


# ---------------------------------------------------------------------------
# gen_path with offsets
# ---------------------------------------------------------------------------


class TestGenPathWithOffsets:
    """Tests for gen_path with episode_offset and season_offset parameters."""

    def test_episode_offset_positive(self):
        """Episode offset adds to episode number."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=5, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi", method="pn", episode_offset=12)
        assert "E17" in result  # 5 + 12 = 17

    def test_episode_offset_negative(self):
        """Negative episode offset subtracts from episode number."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=15, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi", method="pn", episode_offset=-12)
        assert "E03" in result  # 15 - 12 = 3

    def test_episode_offset_negative_below_one_ignored(self):
        """Negative offset that would go below 1 is ignored."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=5, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi", method="pn", episode_offset=-10)
        assert "E05" in result  # Would be -5, so offset ignored

    def test_season_offset_positive(self):
        """Season offset adds to season number."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=5, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi", method="pn", season_offset=1)
        assert "S02" in result  # 1 + 1 = 2

    def test_season_offset_negative(self):
        """Negative season offset subtracts from season number."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=3, episode=5, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi", method="pn", season_offset=-1)
        assert "S02" in result  # 3 - 1 = 2

    def test_season_offset_negative_below_one_ignored(self):
        """Negative season offset that would go below 1 is ignored."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=5, suffix=".mkv"
        )
        result = Renamer.gen_path(ep, "Bangumi", method="pn", season_offset=-5)
        assert "S01" in result  # Would be -4, so offset ignored

    def test_both_offsets_combined(self):
        """Both episode and season offset applied together."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=13, suffix=".mkv"
        )
        result = Renamer.gen_path(
            ep, "Bangumi", method="pn", episode_offset=-12, season_offset=1
        )
        assert "S02E01" in result  # Season 1+1=2, Episode 13-12=1

    def test_offset_with_advance_method(self):
        """Offset works with advance rename method."""
        ep = EpisodeFile(
            media_path="old.mkv", title="My Anime", season=1, episode=25, suffix=".mkv"
        )
        result = Renamer.gen_path(
            ep, "Bangumi Name", method="advance", episode_offset=-12
        )
        assert result == "Bangumi Name S01E13.mkv"

    def test_offset_with_subtitle_method(self):
        """Offset works with subtitle rename methods."""
        sub = SubtitleFile(
            media_path="sub.ass",
            title="My Anime",
            season=1,
            episode=25,
            language="zh",
            suffix=".ass",
        )
        result = Renamer.gen_path(
            sub, "Bangumi", method="subtitle_pn", episode_offset=-12
        )
        assert "E13" in result  # 25 - 12 = 13

    def test_offset_none_method_unchanged(self):
        """None method returns original path regardless of offset."""
        ep = EpisodeFile(
            media_path="original/path/file.mkv",
            title="Test",
            season=1,
            episode=1,
            suffix=".mkv",
        )
        result = Renamer.gen_path(ep, "Bangumi", method="none", episode_offset=100)
        assert result == "original/path/file.mkv"


# ---------------------------------------------------------------------------
# _lookup_offsets
# ---------------------------------------------------------------------------


class TestLookupOffsets:
    """Tests for Renamer._lookup_offsets method with multi-tier lookup."""

    @pytest.fixture
    def renamer(self, mock_qb_client):
        """Create Renamer with mocked internals."""
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.type = "qbittorrent"
            mock_settings.downloader.host = "localhost:8080"
            mock_settings.downloader.username = "admin"
            mock_settings.downloader.password = "admin"
            mock_settings.downloader.ssl = False
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            with patch(
                "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
                return_value=mock_qb_client,
            ):
                r = Renamer()
        r.client = mock_qb_client
        return r

    def test_lookup_by_qb_hash(self, renamer, db_session):
        """First priority: lookup by qb_hash in Torrent table."""
        from module.database.bangumi import BangumiDatabase
        from module.database.torrent import TorrentDatabase
        from module.models import Bangumi, Torrent

        # Create bangumi with offsets
        bangumi_db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Test Anime",
            year="2024",
            title_raw="test_raw",
            season=1,
            episode_offset=-12,
            season_offset=1,
        )
        bangumi_db.add(bangumi)

        # Create torrent linked to bangumi
        torrent_db = TorrentDatabase(db_session)
        torrent = Torrent(
            name="Test Torrent",
            url="https://example.com/torrent",
            bangumi_id=bangumi.id,
            qb_hash="abc123hash",
        )
        torrent_db.add(torrent)

        with patch("module.manager.renamer.Database") as MockDatabase:
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            mock_db.torrent = TorrentDatabase(db_session)
            mock_db.bangumi = BangumiDatabase(db_session)
            MockDatabase.return_value = mock_db

            episode_offset, season_offset = renamer._lookup_offsets(
                torrent_hash="abc123hash",
                torrent_name="irrelevant",
                save_path="/irrelevant/path",
                tags="",
            )

        assert episode_offset == -12
        assert season_offset == 1

    def test_lookup_by_tag_when_hash_not_found(self, renamer, db_session):
        """Second priority: lookup by ab:ID tag when qb_hash not found."""
        from module.database.bangumi import BangumiDatabase
        from module.database.torrent import TorrentDatabase
        from module.models import Bangumi

        # Create bangumi with offsets
        bangumi_db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Tagged Anime",
            year="2024",
            title_raw="tagged_raw",
            season=1,
            episode_offset=5,
            season_offset=0,
        )
        bangumi_db.add(bangumi)

        with patch("module.manager.renamer.Database") as MockDatabase:
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            mock_db.torrent = TorrentDatabase(db_session)
            mock_db.bangumi = BangumiDatabase(db_session)
            MockDatabase.return_value = mock_db

            episode_offset, season_offset = renamer._lookup_offsets(
                torrent_hash="nonexistent_hash",
                torrent_name="irrelevant",
                save_path="/irrelevant/path",
                tags=f"ab:{bangumi.id}",
            )

        assert episode_offset == 5
        assert season_offset == 0

    def test_lookup_by_torrent_name(self, renamer, db_session):
        """Third priority: lookup by torrent name matching title_raw."""
        from module.database.bangumi import BangumiDatabase
        from module.database.torrent import TorrentDatabase
        from module.models import Bangumi

        # Create bangumi with offsets
        bangumi_db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Name Match Anime",
            year="2024",
            title_raw="[SubGroup] Name Match",
            season=1,
            episode_offset=-6,
            season_offset=2,
        )
        bangumi_db.add(bangumi)

        with patch("module.manager.renamer.Database") as MockDatabase:
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            mock_db.torrent = TorrentDatabase(db_session)
            mock_db.bangumi = BangumiDatabase(db_session)
            MockDatabase.return_value = mock_db

            episode_offset, season_offset = renamer._lookup_offsets(
                torrent_hash="nonexistent_hash",
                torrent_name="[SubGroup] Name Match - 01 [1080p].mkv",
                save_path="/irrelevant/path",
                tags="",
            )

        assert episode_offset == -6
        assert season_offset == 2

    def test_lookup_by_save_path_fallback(self, renamer, db_session):
        """Fourth priority: lookup by save_path when other methods fail."""
        from module.database.bangumi import BangumiDatabase
        from module.database.torrent import TorrentDatabase
        from module.models import Bangumi

        # Create bangumi with offsets and save_path
        bangumi_db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Path Match Anime",
            year="2024",
            title_raw="unique_raw_that_wont_match",
            season=1,
            save_path="/downloads/Bangumi/Path Match Anime (2024)/Season 1",
            episode_offset=10,
            season_offset=-1,
        )
        bangumi_db.add(bangumi)

        with patch("module.manager.renamer.Database") as MockDatabase:
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            mock_db.torrent = TorrentDatabase(db_session)
            mock_db.bangumi = BangumiDatabase(db_session)
            MockDatabase.return_value = mock_db

            episode_offset, season_offset = renamer._lookup_offsets(
                torrent_hash="nonexistent_hash",
                torrent_name="completely_different_name.mkv",
                save_path="/downloads/Bangumi/Path Match Anime (2024)/Season 1",
                tags="",
            )

        assert episode_offset == 10
        assert season_offset == -1

    def test_lookup_returns_zero_when_not_found(self, renamer, db_session):
        """Returns (0, 0) when no matching bangumi found."""
        from module.database.bangumi import BangumiDatabase
        from module.database.torrent import TorrentDatabase

        with patch("module.manager.renamer.Database") as MockDatabase:
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            mock_db.torrent = TorrentDatabase(db_session)
            mock_db.bangumi = BangumiDatabase(db_session)
            MockDatabase.return_value = mock_db

            episode_offset, season_offset = renamer._lookup_offsets(
                torrent_hash="nonexistent",
                torrent_name="no_match",
                save_path="/no/match/path",
                tags="",
            )

        assert episode_offset == 0
        assert season_offset == 0

    def test_lookup_skips_deleted_bangumi(self, renamer, db_session):
        """Skips deleted bangumi even if hash/tag matches."""
        from module.database.bangumi import BangumiDatabase
        from module.database.torrent import TorrentDatabase
        from module.models import Bangumi

        # Create deleted bangumi
        bangumi_db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Deleted Anime",
            year="2024",
            title_raw="deleted_raw",
            season=1,
            episode_offset=99,
            season_offset=99,
            deleted=True,
        )
        bangumi_db.add(bangumi)

        with patch("module.manager.renamer.Database") as MockDatabase:
            mock_db = MagicMock()
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            mock_db.torrent = TorrentDatabase(db_session)
            mock_db.bangumi = BangumiDatabase(db_session)
            MockDatabase.return_value = mock_db

            episode_offset, season_offset = renamer._lookup_offsets(
                torrent_hash="nonexistent",
                torrent_name="no_match",
                save_path="/no/match",
                tags=f"ab:{bangumi.id}",
            )

        # Should return (0, 0) because bangumi is deleted
        assert episode_offset == 0
        assert season_offset == 0

    def test_lookup_handles_database_exception(self, renamer):
        """Returns (0, 0) when database throws exception."""
        with patch("module.manager.renamer.Database") as MockDatabase:
            MockDatabase.side_effect = Exception("Database connection failed")

            episode_offset, season_offset = renamer._lookup_offsets(
                torrent_hash="any",
                torrent_name="any",
                save_path="/any",
                tags="",
            )

        assert episode_offset == 0
        assert season_offset == 0
