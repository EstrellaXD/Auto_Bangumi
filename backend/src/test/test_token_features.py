"""Tests for CJK sub-word scanning in the tokenizer classify stage."""

from module.parser.analyser.raw_parser import raw_parser
from module.parser.analyser.tokenizer.stage_classify import _try_cjk_subword
from module.parser.analyser.tokenizer.token import Token, TokenKind

# ---------------------------------------------------------------------------
# CJK sub-word scanning
# ---------------------------------------------------------------------------


class TestCjkSubwordScan:
    def test_gekijouban_simple(self):
        token = Token(text="剧场版", kind=TokenKind.UNKNOWN, position=0, enclosed=False)
        assert _try_cjk_subword(token) is True
        assert token.kind == TokenKind.MOVIE

    def test_gekijouban_traditional(self):
        token = Token(text="劇場版", kind=TokenKind.UNKNOWN, position=0, enclosed=False)
        assert _try_cjk_subword(token) is True
        assert token.kind == TokenKind.MOVIE

    def test_compound_movie_extra(self):
        """'剧场版合集' contains both MOVIE and EXTRA sub-words. MOVIE wins (longer)."""
        token = Token(
            text="剧场版合集", kind=TokenKind.UNKNOWN, position=0, enclosed=False
        )
        assert _try_cjk_subword(token) is True
        assert token.kind == TokenKind.MOVIE

    def test_gashuuhen(self):
        token = Token(text="合集", kind=TokenKind.UNKNOWN, position=0, enclosed=False)
        assert _try_cjk_subword(token) is True
        assert token.kind == TokenKind.EXTRA

    def test_soushuurhen(self):
        token = Token(text="总集篇", kind=TokenKind.UNKNOWN, position=0, enclosed=False)
        assert _try_cjk_subword(token) is True
        assert token.kind == TokenKind.EXTRA

    def test_tokuten(self):
        token = Token(text="特典", kind=TokenKind.UNKNOWN, position=0, enclosed=False)
        assert _try_cjk_subword(token) is True
        assert token.kind == TokenKind.EXTRA

    def test_no_match_plain_cjk(self):
        token = Token(
            text="进击的巨人", kind=TokenKind.UNKNOWN, position=0, enclosed=False
        )
        assert _try_cjk_subword(token) is False
        assert token.kind == TokenKind.UNKNOWN

    def test_no_match_latin_only(self):
        token = Token(text="Movie", kind=TokenKind.UNKNOWN, position=0, enclosed=False)
        assert _try_cjk_subword(token) is False

    def test_no_match_digits(self):
        token = Token(text="2023", kind=TokenKind.UNKNOWN, position=0, enclosed=False)
        assert _try_cjk_subword(token) is False


# ---------------------------------------------------------------------------
# Integration: raw_parser end-to-end with CJK sub-words
# ---------------------------------------------------------------------------


class TestMovieCjkSubwordIntegration:
    def test_gekijouban_gashuuhen_compound(self):
        """'剧场版合集' should be recognized as movie."""
        content = "[SubGroup] 剧场版合集 - 进击的巨人 [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_traditional_gekijouban_spy_family(self):
        content = "[SubGroup] 劇場版 SPY×FAMILY 2023 [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_gekijouban_madoka_gashuuhen(self):
        content = "[LoliHouse] 劇場版 魔法少女まどか☆マギカ 合集 [BDRip 1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is True

    def test_gashuuhen_not_movie(self):
        """'合集' alone should mark as EXTRA, not MOVIE."""
        content = "[SubGroup] 进击的巨人 合集 [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.is_movie is False
        if info.title_zh:
            assert "合集" not in info.title_zh


class TestYearClassification:
    def test_year_not_episode(self):
        """'2023' in a title context should not become the episode number."""
        content = "[SubGroup] 劇場版 SPY×FAMILY 2023 [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.episode != 2023

    def test_year_in_existing_format(self):
        """Year in date format should stay as EXTRA."""
        content = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
        info = raw_parser(content)
        assert info is not None
        assert info.episode == 747
