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
