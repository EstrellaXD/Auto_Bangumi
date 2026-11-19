"""排除过滤词编译（compile_filter）以及 RSS 侧对空过滤词的处理。"""

import re

from module.utils.filter_pattern import compile_filter


def test_blank_terms_are_dropped():
    """设置里多留一个空项时，"720|" 的空分支会匹配所有标题、排除全部种子。"""
    pattern = compile_filter(["720", "", "  "])
    assert pattern is not None
    assert pattern.search("[Sub] Title - 01 [720p]")
    assert pattern.search("[Sub] Title - 01 [1080p]") is None


def test_no_valid_terms_means_no_filter():
    assert compile_filter([]) is None
    assert compile_filter(["", " "]) is None


def test_invalid_regex_falls_back_to_literal():
    pattern = compile_filter(["[简", "720"])
    assert pattern is not None
    assert pattern.search("[简体] Title")
    assert pattern.search("Title [1080p]") is None


def test_flags_are_applied():
    pattern = compile_filter(["hevc"], re.IGNORECASE)
    assert pattern is not None
    assert pattern.search("Title [HEVC]")


def test_rss_engine_rule_filter_with_trailing_comma():
    """规则 filter 由全局过滤词用逗号拼成，末尾多一个逗号不能排除所有种子。"""
    from module.rss.engine import RSSEngine

    engine = RSSEngine.__new__(RSSEngine)
    engine._filter_cache = {}
    pattern = engine._get_filter_pattern("720,")
    assert pattern is not None
    assert pattern.search("Title [1080p]") is None
    assert engine._get_filter_pattern(",") is None
