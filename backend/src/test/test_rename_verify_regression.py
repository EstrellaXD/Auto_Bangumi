"""Regression tests reproducing the rename-verify false-positive (#754 / #749).

The bug: ``torrents_rename_file`` treated a qBittorrent ``renameFile`` 200 that
did NOT actually rename the file (old name still present, e.g. while seeding or
when the target already exists) as success, because the verify loop fell through
to ``return True`` after the ``break``/"neither found" paths. AB then re-renamed
+ re-notified every cycle ("重命名一直在重复 / 不停止").

These tests pin the corrected contract: only return True when ``new_path``
actually appears; otherwise return False so the caller backs off via the pending
cooldown. ``test_verify_false_when_file_keeps_old_name`` is the direct repro —
it FAILS on the pre-fix code (returns True) and PASSES after the fix.
"""

import pytest

from module.downloader.client.qb_downloader import QbDownloader


class _Resp:
    def __init__(self, code: int):
        self.status_code = code


def _make_qb(file_list, post_code: int = 200):
    """A QbDownloader with the network calls stubbed.

    ``file_list`` is what ``torrents_files`` reports on every poll (the rename
    either took effect or it didn't — we keep it constant across the retries).
    """
    qb = QbDownloader.__new__(QbDownloader)
    qb.host = "http://qb"

    class _Client:
        async def post(self, url, data=None):
            return _Resp(post_code)

    qb._client = _Client()

    async def _files(_hash):
        return file_list

    qb.torrents_files = _files
    return qb


@pytest.mark.asyncio
async def test_verify_false_when_file_keeps_old_name():
    # Direct repro of #754/#749: API 200 but the file is never renamed.
    qb = _make_qb([{"name": "old.mkv"}])
    assert await qb.torrents_rename_file("h", "old.mkv", "new.mkv") is False


@pytest.mark.asyncio
async def test_verify_false_when_neither_name_present():
    # Multi-file torrent where the polled list shows neither name yet.
    qb = _make_qb([{"name": "unrelated.mkv"}])
    assert await qb.torrents_rename_file("h", "old.mkv", "new.mkv") is False


@pytest.mark.asyncio
async def test_verify_true_when_new_path_appears():
    # Sanity: a real, verified rename still returns True.
    qb = _make_qb([{"name": "new.mkv"}])
    assert await qb.torrents_rename_file("h", "old.mkv", "new.mkv") is True


@pytest.mark.asyncio
async def test_verify_409_conflict_is_false():
    # Target already exists (another source got there first) → not our rename.
    qb = _make_qb([{"name": "old.mkv"}], post_code=409)
    assert await qb.torrents_rename_file("h", "old.mkv", "new.mkv") is False
