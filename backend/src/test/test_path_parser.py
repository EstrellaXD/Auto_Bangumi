from unittest.mock import patch

from module.conf import PLATFORM


def test_path_to_bangumi():
    # Test for unix-like path
    from module.downloader.path import TorrentPath

    path = "Downloads/Bangumi/Kono Subarashii Sekai ni Shukufuku wo!/Season 2/"
    bangumi_name, season = TorrentPath()._path_to_bangumi(path)
    assert bangumi_name == "Kono Subarashii Sekai ni Shukufuku wo!"
    assert season == 2


class TestGenSavePath:
    """Tests for TorrentPath._gen_save_path with season_offset."""

    def test_gen_save_path_no_offset(self):
        """Save path uses season directly when no offset."""
        from module.downloader.path import TorrentPath
        from module.models import Bangumi

        bangumi = Bangumi(
            official_title="Test Anime",
            year="2024",
            season=1,
            season_offset=0,
            title_raw="test",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert "Season 1" in result
        assert "Test Anime (2024)" in result

    def test_gen_save_path_with_positive_offset(self):
        """Save path uses adjusted season when offset is positive."""
        from module.downloader.path import TorrentPath
        from module.models import Bangumi

        bangumi = Bangumi(
            official_title="Test Anime",
            year="2024",
            season=1,
            season_offset=1,
            title_raw="test",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert "Season 2" in result  # 1 + 1 = 2
        assert "Test Anime (2024)" in result

    def test_gen_save_path_with_negative_offset(self):
        """Save path uses adjusted season when offset is negative."""
        from module.downloader.path import TorrentPath
        from module.models import Bangumi

        bangumi = Bangumi(
            official_title="Test Anime",
            year="2024",
            season=3,
            season_offset=-1,
            title_raw="test",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert "Season 2" in result  # 3 - 1 = 2

    def test_gen_save_path_offset_below_one_ignored(self):
        """Save path doesn't go below Season 1."""
        from module.downloader.path import TorrentPath
        from module.models import Bangumi

        bangumi = Bangumi(
            official_title="Test Anime",
            year="2024",
            season=1,
            season_offset=-5,
            title_raw="test",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert "Season 1" in result  # Would be -4, so uses original season
