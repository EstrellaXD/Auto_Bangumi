import pytest

from module.parser.analyser import raw_parser


class TestMovieMarkerDetection:
    def test_gekijouban_chinese_traditional(self):
        content = "[SubGroup] 劇場版 Some Anime Title [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_gekijouban_chinese_simplified(self):
        content = "[SubGroup] 剧场版 Some Anime Title [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_movie_keyword_english(self):
        content = "[SubGroup] Some Anime Title Movie [1080p HEVC]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_gekijouban_romaji(self):
        content = "[SubGroup] Gekijouban Some Anime [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_movie_keyword_case_insensitive(self):
        content = "[SubGroup] Some Anime MOVIE [720p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_gekijouban_with_hyphen(self):
        content = "[SubGroup] Gekijou-ban Title [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_movie_defaults(self):
        """Movies should default to episode=0, season=1."""
        content = "[SubGroup] 劇場版 Anime Title [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True
        assert info.episode == 0
        assert info.season == 1


class TestNonMovieRegression:
    def test_regular_episode_not_movie(self):
        content = "[LoliHouse] Some Anime - 01 [WebRip 1080p HEVC-10bit AAC]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is False
        assert info.episode == 1

    def test_regular_series_with_season(self):
        content = "【幻樱字幕组】【Anime Title S02】【12】【GB_MP4】【1920X1080】"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is False
        assert info.season == 2
        assert info.episode == 12

    def test_regular_series_chinese_episode(self):
        content = "[字幕组] 动画标题 第5话 [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is False
        assert info.episode == 5

    def test_end_marker_not_movie(self):
        content = "[LoliHouse] Anime Title - 12 [WebRip 1080p HEVC-10bit AAC][END]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is False
        assert info.episode == 12
