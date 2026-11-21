"""Tests for the Mikan homepage parser's module-level cache."""

import importlib

# `module.parser.analyser.__init__` re-exports the `mikan_parser` function under
# the same name as this submodule, shadowing the submodule on the package
# object — so `import module.parser.analyser.mikan_parser as x` would resolve
# to the function, not the module. Go through importlib to get the module.
mikan_parser_module = importlib.import_module("module.parser.analyser.mikan_parser")


def test_reset_cache_clears_mikan_cache():
    """reset_cache() must drop all cached homepage lookups (called on config
    reload so a changed endpoint stops serving stale results)."""
    mikan_parser_module._mikan_cache["https://mikanani.me/Home/Episode/stale"] = (
        "",
        "Stale Title",
    )
    assert len(mikan_parser_module._mikan_cache) > 0

    mikan_parser_module.reset_cache()

    assert len(mikan_parser_module._mikan_cache) == 0


async def _parse_with_style(style: str):
    from unittest.mock import AsyncMock, MagicMock, patch

    html = (
        f'<div class="bangumi-poster" style="{style}"></div>'
        '<p class="bangumi-title"><a href="/Home/Bangumi/1">葬送的芙莉莲 第二季</a></p>'
    )
    req = MagicMock()
    req.get_html = AsyncMock(return_value=html)
    req.get_content = AsyncMock(return_value=None)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=req)
    ctx.__aexit__ = AsyncMock(return_value=None)
    homepage = f"https://mikanani.me/Home/Episode/{abs(hash(style))}"
    with patch.object(mikan_parser_module, "RequestContent", return_value=ctx):
        result = await mikan_parser_module.mikan_parser(homepage)
    return result, req


async def test_poster_url_without_quotes_is_parsed():
    """url() 不带引号时也能取到海报地址，不再因 split 越界抛 IndexError。"""
    result, req = await _parse_with_style(
        "background-image: url(/images/Bangumi/1.jpg?width=400)"
    )
    req.get_content.assert_awaited_once_with("https://mikanani.me/images/Bangumi/1.jpg")
    assert result == ("", "葬送的芙莉莲")


async def test_poster_style_without_url_skips_poster():
    result, req = await _parse_with_style("background-color: #000")
    req.get_content.assert_not_awaited()
    assert result == ("", "葬送的芙莉莲")
