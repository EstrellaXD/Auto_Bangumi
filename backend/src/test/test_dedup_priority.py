"""Unit tests for the RSS dedup + subtitle-group priority selection.

Covers `RSSEngine._group_rank` and `RSSEngine._select_downloads` (upstream
#660 multi-source dedup / priority source). The selection logic is pure given
a parser + a "already downloaded" lookup, so we bypass the DB by constructing
the engine via ``__new__`` and stubbing ``self.torrent`` + ``raw_parser``.
"""

import re
from types import SimpleNamespace as NS

import pytest

import module.rss.engine as engine_mod
from module.rss.engine import RSSEngine


def _fake_parser(name):
    """Minimal stand-in for raw_parser: group from [..], episode from ' - NN'."""
    group = re.split(r"[\[\]]", name)[1] if "[" in name else ""
    m = re.search(r" - (\d+)", name)
    if not m:
        return None
    return NS(season=1, episode=int(m.group(1)), group=group)


def _bgm(_id):
    return NS(id=_id)


def _torrent(name):
    return NS(name=name, downloaded=False, bangumi_id=None)


@pytest.fixture
def eng(monkeypatch):
    e = RSSEngine.__new__(RSSEngine)  # bypass __init__ (no DB)
    e.torrent = NS(search_downloaded=lambda ids: [])
    monkeypatch.setattr(engine_mod, "raw_parser", _fake_parser)
    return e


def _set_priority(monkeypatch, value):
    monkeypatch.setattr(engine_mod.settings.rss_parser, "group_priority", value)


def test_group_rank_ordering():
    p = ["LoliHouse", "Baha"]
    assert RSSEngine._group_rank("LoliHouse", p) == 0
    assert RSSEngine._group_rank("动漫国&LoliHouse", p) == 0  # substring match
    assert RSSEngine._group_rank("Baha", p) == 1
    assert RSSEngine._group_rank("RandomSub", p) == 2  # unknown ranks last
    assert RSSEngine._group_rank("", p) == 2


def test_dedup_picks_priority_source(eng, monkeypatch):
    _set_priority(monkeypatch, ["LoliHouse", "Baha"])
    bgm = _bgm(42)
    cands = [
        (_torrent("[KitaujiSub] Awajima Hyakkei - 05 [x].mkv"), bgm),
        (_torrent("[LoliHouse] Awajima Hyakkei - 05 [x].mkv"), bgm),
        (_torrent("[TSDM] Awajima Hyakkei - 05 [x].mp4"), bgm),
    ]
    out = eng._select_downloads(cands)
    assert len(out) == 1
    assert "LoliHouse" in out[0][0].name


def test_already_downloaded_episode_skipped(eng, monkeypatch):
    _set_priority(monkeypatch, ["LoliHouse"])
    eng.torrent = NS(
        search_downloaded=lambda ids: [
            NS(name="[LoliHouse] Awajima Hyakkei - 05 [x].mkv", bangumi_id=42)
        ]
    )
    cands = [(_torrent("[TSDM] Awajima Hyakkei - 05 [x].mp4"), _bgm(42))]
    assert eng._select_downloads(cands) == []


def test_empty_priority_is_legacy_keep_all(eng, monkeypatch):
    _set_priority(monkeypatch, [])
    bgm = _bgm(42)
    cands = [(_torrent("a"), bgm), (_torrent("b"), bgm)]
    assert eng._select_downloads(cands) == cands


def test_per_episode_independent_selection(eng, monkeypatch):
    _set_priority(monkeypatch, ["LoliHouse"])
    bgm = _bgm(42)
    cands = [
        (_torrent("[TSDM] Awajima Hyakkei - 05 [x].mp4"), bgm),
        (_torrent("[LoliHouse] Awajima Hyakkei - 05 [x].mkv"), bgm),
        (_torrent("[TSDM] Awajima Hyakkei - 06 [x].mp4"), bgm),
        (_torrent("[LoliHouse] Awajima Hyakkei - 06 [x].mkv"), bgm),
    ]
    out = eng._select_downloads(cands)
    assert len(out) == 2
    assert all("LoliHouse" in t.name for t, _ in out)


def test_unparseable_is_fail_open(eng, monkeypatch):
    _set_priority(monkeypatch, ["LoliHouse"])
    cands = [(_torrent("RandomFileNoEpisode.mkv"), _bgm(42))]
    assert len(eng._select_downloads(cands)) == 1  # kept, not dropped


def test_per_bangumi_priority_overrides_global(eng, monkeypatch):
    _set_priority(monkeypatch, ["TSDM"])  # global prefers TSDM
    bgm = NS(id=42, group_priority='["LoliHouse"]')  # but this sub prefers LoliHouse
    cands = [
        (_torrent("[TSDM] X - 05 [x].mp4"), bgm),
        (_torrent("[LoliHouse] X - 05 [x].mkv"), bgm),
    ]
    out = eng._select_downloads(cands)
    assert len(out) == 1
    assert "LoliHouse" in out[0][0].name  # per-bangumi wins over global


def test_per_bangumi_empty_falls_back_to_global(eng, monkeypatch):
    _set_priority(monkeypatch, ["LoliHouse"])
    bgm = NS(id=42, group_priority=None)  # no per-bangumi → use global
    cands = [
        (_torrent("[TSDM] X - 05 [x].mp4"), bgm),
        (_torrent("[LoliHouse] X - 05 [x].mkv"), bgm),
    ]
    out = eng._select_downloads(cands)
    assert len(out) == 1
    assert "LoliHouse" in out[0][0].name


def test_per_bangumi_priority_with_no_global(eng, monkeypatch):
    _set_priority(monkeypatch, [])  # global dedup off
    bgm = NS(id=42, group_priority='["LoliHouse"]')  # but this sub enables it
    cands = [
        (_torrent("[TSDM] X - 05 [x].mp4"), bgm),
        (_torrent("[LoliHouse] X - 05 [x].mkv"), bgm),
    ]
    out = eng._select_downloads(cands)
    assert len(out) == 1
    assert "LoliHouse" in out[0][0].name  # per-bangumi dedups even when global is off
