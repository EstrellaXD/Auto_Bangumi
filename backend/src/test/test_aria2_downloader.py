"""Tests for Aria2Downloader: JSON-RPC error handling, add/query/rename/manage.

Mirrors test_qb_downloader.py's approach: low-level RPC behaviour is verified
by patching ``self._client`` directly (mock JSON-RPC transport); higher-level
business logic (dedup, gid<->bangumi association, filesystem rename/move) is
verified by patching ``Aria2Downloader._call`` and letting the real logic
(including the real, per-test temp-file DB from conftest's autouse
``_bind_bare_database`` fixture) run.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from module.database import Database
from module.database.aria2 import Aria2RenameIntent
from module.downloader import AddResult, RenameOutcome
from module.downloader.client.aria2_downloader import (
    Aria2ConnectionError,
    Aria2Downloader,
    Aria2RpcError,
)


def _aria2() -> Aria2Downloader:
    return Aria2Downloader("http://localhost:6800", "u", "secret-token")


def _rename_intent(old_path: str, new_path: str, source) -> Aria2RenameIntent:
    stat_result = source.stat()
    return Aria2RenameIntent(
        old_path=old_path,
        new_path=new_path,
        st_dev=stat_result.st_dev,
        st_ino=stat_result.st_ino,
        st_size=stat_result.st_size,
        st_mtime_ns=stat_result.st_mtime_ns,
    )


def _rpc_response(result=None, error=None):
    resp = MagicMock()
    body: dict = {"jsonrpc": "2.0", "id": 1}
    if error is not None:
        body["error"] = error
    else:
        body["result"] = result
    resp.json.return_value = body
    return resp


# ---------------------------------------------------------------------------
# _call: low-level JSON-RPC transport
# ---------------------------------------------------------------------------


class TestCallRpcLayer:
    async def test_call_success_returns_result(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        aria2._client.post = AsyncMock(return_value=_rpc_response(result="1.36.0"))

        result = await aria2._call("getVersion")

        assert result == "1.36.0"

    async def test_call_prepends_token_as_first_param(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        aria2._client.post = AsyncMock(return_value=_rpc_response(result=[]))

        await aria2._call("tellActive", [1, 2])

        payload = aria2._client.post.call_args.kwargs["json"]
        assert payload["params"] == ["token:secret-token", 1, 2]
        assert payload["method"] == "aria2.tellActive"

    async def test_call_error_response_raises_aria2_rpc_error(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        aria2._client.post = AsyncMock(
            return_value=_rpc_response(error={"code": 1, "message": "Unauthorized"})
        )

        with pytest.raises(Aria2RpcError) as excinfo:
            await aria2._call("getVersion")
        assert excinfo.value.code == 1
        assert excinfo.value.message == "Unauthorized"

    async def test_call_timeout_raises_connection_error(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        aria2._client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with pytest.raises(Aria2ConnectionError):
            await aria2._call("getVersion")

    async def test_call_request_error_raises_connection_error(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        aria2._client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with pytest.raises(Aria2ConnectionError):
            await aria2._call("getVersion")

    async def test_call_invalid_json_raises_connection_error(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        bad_resp = MagicMock()
        bad_resp.json.side_effect = ValueError("not json")
        aria2._client.post = AsyncMock(return_value=bad_resp)

        with pytest.raises(Aria2ConnectionError):
            await aria2._call("getVersion")

    async def test_call_uses_default_timeout_when_not_overridden(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        aria2._client.post = AsyncMock(return_value=_rpc_response(result=[]))

        await aria2._call("tellActive")

        assert aria2._client.post.call_args.kwargs["timeout"] == 10.0

    async def test_call_honors_explicit_timeout_override(self):
        aria2 = _aria2()
        aria2._client = AsyncMock()
        aria2._client.post = AsyncMock(return_value=_rpc_response(result=[]))

        await aria2._call("getVersion", timeout=2.5)

        assert aria2._client.post.call_args.kwargs["timeout"] == 2.5

    async def test_call_without_auth_raises_assertion(self):
        aria2 = _aria2()
        with pytest.raises(AssertionError):
            await aria2._call("getVersion")


# ---------------------------------------------------------------------------
# auth()
# ---------------------------------------------------------------------------


class TestAuth:
    async def test_auth_returns_true_on_success(self):
        aria2 = _aria2()
        with patch.object(aria2, "_call", AsyncMock(return_value={"version": "1.0"})):
            result = await aria2.auth()
        assert result is True
        assert aria2._authed is True

    async def test_auth_reuses_already_authed_client(self):
        aria2 = _aria2()
        call_mock = AsyncMock(return_value={"version": "1.0"})
        with patch.object(aria2, "_call", call_mock):
            await aria2.auth()
            await aria2.auth()
        assert call_mock.call_count == 1

    async def test_auth_retries_and_returns_false_on_persistent_rpc_error(self):
        aria2 = _aria2()
        with (
            patch.object(
                aria2, "_call", AsyncMock(side_effect=Aria2RpcError(1, "bad token"))
            ),
            patch(
                "module.downloader.client.aria2_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await aria2.auth(retry=2)
        assert result is False
        assert aria2._authed is False

    async def test_auth_retries_on_connection_error_then_succeeds(self):
        aria2 = _aria2()
        call_mock = AsyncMock(
            side_effect=[Aria2ConnectionError("refused"), {"version": "1.0"}]
        )
        with (
            patch.object(aria2, "_call", call_mock),
            patch(
                "module.downloader.client.aria2_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await aria2.auth(retry=3)
        assert result is True
        assert call_mock.call_count == 2

    async def test_logout_clears_client_and_authed_flag(self):
        aria2 = _aria2()
        with patch.object(aria2, "_call", AsyncMock(return_value={"version": "1.0"})):
            await aria2.auth()
        await aria2.logout()
        assert aria2._client is None
        assert aria2._authed is False


# ---------------------------------------------------------------------------
# add_torrents: honest results + gid tracking + dedup
# ---------------------------------------------------------------------------


class TestAddTorrents:
    async def test_new_url_returns_true_and_persists_gid(self):
        aria2 = _aria2()
        with patch.object(aria2, "_call", AsyncMock(return_value="gid001")):
            result = await aria2.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:abc",
                torrent_files=None,
                save_path="/downloads/Show/Season 1",
                category="Bangumi",
                tags="ab:42",
            )
        assert result is AddResult.ADDED
        async with Database() as db:
            record = await db.aria2.get("gid001")
        assert record is not None
        assert record.bangumi_id == 42
        assert record.category == "Bangumi"

    async def test_magnet_followed_by_gid_is_persisted(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "addUri":
                return "metadata-gid"
            if method == "tellStatus":
                return {"followedBy": ["payload-gid"]}
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:abc",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:42",
            )

        assert result is AddResult.ADDED
        async with Database() as db:
            assert await db.aria2.get("metadata-gid") is None
            record = await db.aria2.get("payload-gid")
        assert record is not None
        assert record.bangumi_id == 42
        assert record.dedup_key == "url:magnet:?xt=urn:btih:abc"

    async def test_duplicate_url_second_call_returns_false_and_skips_rpc(self):
        aria2 = _aria2()
        add_uri_calls = []

        async def fake_call(method, params=None, timeout=10.0):
            if method == "addUri":
                add_uri_calls.append(params)
                return "gid001"
            if method == "tellStatus":
                # 记录仍活在 aria2 中 -> 真重复。
                return {"status": "active"}
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            await aria2.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:abc",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:1",
            )
            result = await aria2.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:abc",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:1",
            )
        assert result is AddResult.DUPLICATE
        # addUri only called once -- the second, duplicate add never hit aria2.
        assert len(add_uri_calls) == 1

    async def test_partial_duplicate_returns_true(self):
        aria2 = _aria2()
        add_uri_calls = []

        async def fake_call(method, params=None, timeout=10.0):
            if method == "addUri":
                add_uri_calls.append(params)
                return f"gid{len(add_uri_calls):03d}"
            if method == "tellStatus":
                return {"status": "active"}
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            await aria2.add_torrents(
                torrent_urls=["magnet:?xt=urn:btih:aaa"],
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:1",
            )
            result = await aria2.add_torrents(
                torrent_urls=["magnet:?xt=urn:btih:aaa", "magnet:?xt=urn:btih:bbb"],
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:1",
            )
        assert result is AddResult.ADDED
        assert len(add_uri_calls) == 2

    async def test_all_urls_already_added_returns_false(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "addUri":
                return "gid001"
            if method == "tellStatus":
                return {"status": "active"}
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            await aria2.add_torrents(
                torrent_urls=["magnet:?xt=urn:btih:aaa"],
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:1",
            )
            result = await aria2.add_torrents(
                torrent_urls=["magnet:?xt=urn:btih:aaa"],
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:1",
            )
        assert result is AddResult.DUPLICATE

    async def test_rpc_duplicate_error_treated_as_already_added(self):
        aria2 = _aria2()
        with patch.object(
            aria2,
            "_call",
            AsyncMock(side_effect=Aria2RpcError(1, "GID already exists")),
        ):
            result = await aria2.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:zzz",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )
        assert result is AddResult.DUPLICATE
        async with Database() as db:
            # Nothing to persist -- addUri never returned a gid.
            assert (
                await db.aria2.find_by_dedup_key("url:magnet:?xt=urn:btih:zzz") is None
            )

    async def test_rpc_non_duplicate_error_returns_false_for_that_item(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(side_effect=Aria2RpcError(3, "Disk full"))
        ):
            result = await aria2.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:zzz",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )
        assert result is AddResult.FAILED

    async def test_torrent_file_bytes_dedup_by_content_hash(self):
        aria2 = _aria2()
        add_torrent_calls = []
        payload = b"fake torrent bytes"

        async def fake_call(method, params=None, timeout=10.0):
            if method == "addTorrent":
                add_torrent_calls.append(params)
                return "gid-file-1"
            if method == "tellStatus":
                return {"status": "active"}
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            first = await aria2.add_torrents(
                torrent_urls=None,
                torrent_files=payload,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:7",
            )
            second = await aria2.add_torrents(
                torrent_urls=None,
                torrent_files=payload,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:7",
            )
        assert first is AddResult.ADDED
        assert second is AddResult.DUPLICATE
        assert len(add_torrent_calls) == 1

    async def test_add_torrents_stale_dedup_gid_not_found_readds(self):
        """aria2 报 not found（例如无 --save-session 重启后）→ 删陈旧记录并重新添加。"""
        aria2 = _aria2()
        url = "magnet:?xt=urn:btih:abc"
        async with Database() as db:
            await db.aria2.upsert(
                "gid-stale", bangumi_id=1, category="Bangumi", dedup_key=f"url:{url}"
            )

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                raise Aria2RpcError(1, "GID#gid-stale is not found")
            if method == "addUri":
                return "gid-fresh"
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.add_torrents(
                torrent_urls=url,
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags="ab:1",
            )

        assert result is AddResult.ADDED
        async with Database() as db:
            assert await db.aria2.get("gid-stale") is None
            assert await db.aria2.get("gid-fresh") is not None

    async def test_add_torrents_stale_dedup_gid_removed_status_readds(self):
        """gid 还在 aria2 里但 status 是 removed（用户在 UI 删除）→ 视作陈旧，重新添加。"""
        aria2 = _aria2()
        url = "magnet:?xt=urn:btih:abc"
        async with Database() as db:
            await db.aria2.upsert("gid-removed", dedup_key=f"url:{url}")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"status": "removed"}
            if method == "addUri":
                return "gid-fresh"
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.add_torrents(
                torrent_urls=url,
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

        assert result is AddResult.ADDED
        async with Database() as db:
            assert await db.aria2.get("gid-removed") is None
            assert await db.aria2.get("gid-fresh") is not None

    async def test_add_torrents_dedup_gid_still_active_skips_readd(self):
        """gid 仍活在 aria2 中 → 真重复，不重新添加。"""
        aria2 = _aria2()
        url = "magnet:?xt=urn:btih:abc"
        async with Database() as db:
            await db.aria2.upsert("gid-alive", dedup_key=f"url:{url}")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"status": "active"}
            if method == "addUri":  # pragma: no cover - 不应该走到这里
                raise AssertionError("addUri must not be called for a live duplicate")
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.add_torrents(
                torrent_urls=url,
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

        assert result is AddResult.DUPLICATE
        async with Database() as db:
            assert await db.aria2.get("gid-alive") is not None

    async def test_add_torrents_dedup_verify_unreachable_keeps_record_and_skips(self):
        """aria2 不可达时不能断定记录陈旧：保留本地记录，也不重复添加。"""
        aria2 = _aria2()
        url = "magnet:?xt=urn:btih:abc"
        async with Database() as db:
            await db.aria2.upsert("gid-unknown", dedup_key=f"url:{url}")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                raise Aria2ConnectionError("down")
            if method == "addUri":  # pragma: no cover - 不应该走到这里
                raise AssertionError("addUri must not be called when unverifiable")
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.add_torrents(
                torrent_urls=url,
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

        assert result is AddResult.FAILED
        async with Database() as db:
            assert await db.aria2.get("gid-unknown") is not None

    async def test_add_torrents_stale_dedup_torrent_file_readds(self):
        """种子文件走 content-hash 去重，同样要做陈旧校验。"""
        aria2 = _aria2()
        import hashlib

        payload = b"fake torrent bytes"
        dedup_key = f"file:{hashlib.sha1(payload).hexdigest()}"
        async with Database() as db:
            await db.aria2.upsert("gid-stale-file", dedup_key=dedup_key)

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                raise Aria2RpcError(1, "GID#gid-stale-file is not found")
            if method == "addTorrent":
                return "gid-fresh-file"
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.add_torrents(
                torrent_urls=None,
                torrent_files=payload,
                save_path="/downloads",
                category="Bangumi",
            )

        assert result is AddResult.ADDED
        async with Database() as db:
            assert await db.aria2.get("gid-stale-file") is None
            assert await db.aria2.get("gid-fresh-file") is not None

    async def test_no_tags_leaves_bangumi_id_unset(self):
        aria2 = _aria2()
        with patch.object(aria2, "_call", AsyncMock(return_value="gid-no-tag")):
            await aria2.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:notag",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
                tags=None,
            )
        async with Database() as db:
            record = await db.aria2.get("gid-no-tag")
        assert record is not None
        assert record.bangumi_id is None


# ---------------------------------------------------------------------------
# torrents_info: aria2 -> qB-shaped dict mapping
# ---------------------------------------------------------------------------


def _download(gid, status="complete", dir_="/downloads/Show/Season 1", name=None):
    d = {
        "gid": gid,
        "status": status,
        "dir": dir_,
        "totalLength": "1000",
        "completedLength": "1000" if status == "complete" else "500",
        "downloadSpeed": "0",
        "uploadSpeed": "0",
        "files": [{"path": f"{dir_}/{name or gid}.mkv"}],
    }
    return d


class TestTorrentsInfo:
    async def test_maps_fields_to_qb_shape(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [_download("gidA", status="active")]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            async with Database() as db:
                await db.aria2.upsert("gidA", bangumi_id=5, category="Bangumi")
            result = await aria2.torrents_info(status_filter=None, category=None)

        assert len(result) == 1
        info = result[0]
        assert info["hash"] == "gidA"
        assert info["save_path"] == "/downloads/Show/Season 1"
        assert info["tags"] == "ab:5"
        assert info["category"] == "Bangumi"
        assert info["state"] == "downloading"  # active + 未完成 → qB 词汇
        assert info["name"] == "gidA.mkv"

    async def test_status_filter_completed_excludes_active(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [_download("gidActive", status="active")]
            if method == "tellStopped":
                return [_download("gidDone", status="complete")]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter="completed", category=None)

        assert [r["hash"] for r in result] == ["gidDone"]

    async def test_status_filter_none_includes_everything(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [_download("gidActive", status="active")]
            if method == "tellStopped":
                return [_download("gidDone", status="complete")]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category=None)

        assert {r["hash"] for r in result} == {"gidActive", "gidDone"}

    async def test_category_filter_excludes_other_categories(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [_download("gidA"), _download("gidB")]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            async with Database() as db:
                await db.aria2.upsert("gidA", category="Bangumi")
                await db.aria2.upsert("gidB", category="Other")
            result = await aria2.torrents_info(status_filter=None, category="Bangumi")

        assert [r["hash"] for r in result] == ["gidA"]

    async def test_untracked_gid_has_no_tag_and_empty_category(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [_download("gidUntracked")]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category=None)

        assert result[0]["tags"] == ""
        assert result[0]["category"] == ""

    async def test_connection_query_failure_is_raised(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(side_effect=Aria2ConnectionError("down"))
        ):
            with pytest.raises(Aria2ConnectionError, match="down"):
                await aria2.torrents_info(status_filter=None, category=None)

    async def test_rpc_query_failure_is_raised(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(side_effect=Aria2RpcError(1, "failed"))
        ):
            with pytest.raises(Aria2RpcError, match="failed"):
                await aria2.torrents_info(status_filter=None, category=None)

    async def test_torrent_exists_returns_true_for_known_gid(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(return_value={"status": "complete"})
        ) as call:
            assert await aria2.torrent_exists("gidA") is True
        call.assert_awaited_once_with("tellStatus", ["gidA", ["status"]])

    async def test_torrent_exists_returns_false_only_for_explicit_not_found(self):
        aria2 = _aria2()
        with patch.object(
            aria2,
            "_call",
            AsyncMock(side_effect=Aria2RpcError(1, "GID#gidA is not found")),
        ):
            assert await aria2.torrent_exists("gidA") is False

    @pytest.mark.parametrize(
        "error",
        [Aria2ConnectionError("down"), Aria2RpcError(1, "Internal error")],
    )
    async def test_torrent_exists_returns_none_when_presence_is_unknown(self, error):
        aria2 = _aria2()
        with patch.object(aria2, "_call", AsyncMock(side_effect=error)):
            assert await aria2.torrent_exists("gidA") is None

    async def test_torrents_info_zero_total_length_progress_is_zero(self):
        """磁力链在拉元数据阶段 totalLength 是字符串 "0"（truthy）——
        不能除零崩掉整个 torrents_info。"""
        aria2 = _aria2()
        download = {
            "gid": "gidMeta",
            "status": "active",
            "dir": "/downloads",
            "totalLength": "0",
            "completedLength": "0",
            "downloadSpeed": "0",
            "uploadSpeed": "0",
            "files": [],
        }

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [download]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category=None)

        assert len(result) == 1
        assert result[0]["progress"] == 0.0
        assert result[0]["size"] == 0

    async def test_torrents_info_provides_ui_fields(self):
        """WebUI 下载页无条件消费 num_seeds/num_leechs/eta/added_on——aria2
        载荷缺了它们会渲染成 'undefined / undefined' 和 'NaNhNaNm'。"""
        aria2 = _aria2()
        download = _download("gidUi", status="active")
        download["numSeeders"] = "3"
        download["connections"] = "8"
        download["downloadSpeed"] = "100"  # 剩余 500 字节 → eta 5s

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [download]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category=None)

        info = result[0]
        assert info["num_seeds"] == 3
        assert info["num_leechs"] == 5  # connections - seeders
        assert info["eta"] == 5
        assert isinstance(info["added_on"], int)

    async def test_torrents_info_eta_infinite_when_stalled(self):
        """下载中但速度为 0：eta 用 qB 的"无穷"约定 8640000（UI 显示 '-'）。"""
        aria2 = _aria2()
        download = _download("gidStall", status="active")  # dlspeed "0"

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [download]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category=None)

        assert result[0]["eta"] == 8640000

    async def test_torrents_info_maps_states_to_qb_vocabulary(self):
        """状态徽标/筛选只认 qB 词汇：active/waiting/paused/complete/error
        必须映射，不能把 aria2 原词直接透传给 UI。"""
        aria2 = _aria2()
        cases = [
            ("active", "500", "downloading"),
            ("active", "1000", "uploading"),  # 下载完成、做种中
            ("waiting", "500", "queuedDL"),
            ("paused", "500", "pausedDL"),
            ("paused", "1000", "pausedUP"),
            ("complete", "1000", "pausedUP"),
            ("error", "500", "error"),
        ]
        downloads = []
        for idx, (status, completed, _) in enumerate(cases):
            d = _download(f"gid{idx}", status=status)
            d["completedLength"] = completed
            downloads.append(d)

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return downloads
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category=None)

        by_gid = {info["hash"]: info["state"] for info in result}
        for idx, (_, _, expected) in enumerate(cases):
            assert by_gid[f"gid{idx}"] == expected, f"case {idx}"

    async def test_torrents_info_string_numbers_parsed_to_int(self):
        """aria2 JSON-RPC 的数值字段都是字符串，映射结果必须是 int/float。"""
        aria2 = _aria2()
        download = _download("gidNum", status="active")
        download["downloadSpeed"] = "12345"
        download["uploadSpeed"] = "678"

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [download]
            return []

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category=None)

        info = result[0]
        assert info["size"] == 1000
        assert info["progress"] == 0.5
        assert info["dlspeed"] == 12345
        assert info["upspeed"] == 678

    async def test_torrents_info_migrates_followed_by_gid_metadata(self):
        aria2 = _aria2()
        stub = _download("metadata-gid", status="complete")
        stub["followedBy"] = ["payload-gid"]
        payload = _download("payload-gid", status="active")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellActive":
                return [payload]
            if method == "tellStopped":
                return [stub]
            return []

        async with Database() as db:
            await db.aria2.upsert("metadata-gid", bangumi_id=5, category="Bangumi")

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_info(status_filter=None, category="Bangumi")

        # 元数据 stub 必须被跳过，只报告真实下载（follower gid），否则 stub
        # 会以完成态混进重命名循环、UI 里出现重复条目
        assert [t["hash"] for t in result] == ["payload-gid"]
        assert result[0]["tags"] == "ab:5"
        assert result[0]["category"] == "Bangumi"
        async with Database() as db:
            assert await db.aria2.get("metadata-gid") is None
            assert await db.aria2.get("payload-gid") is not None


# ---------------------------------------------------------------------------
# aria2_gid durable rename intent repository
# ---------------------------------------------------------------------------


class TestRenameIntentDatabase:
    async def test_persists_and_reads_typed_rename_intent(self, tmp_path):
        source = tmp_path / "old.mkv"
        source.write_bytes(b"data")
        intent = _rename_intent("old.mkv", "new.mkv", source)

        async with Database() as db:
            await db.aria2.set_rename_intent("gidA", intent)
            assert await db.aria2.get_rename_intent("gidA") == intent
            record = await db.aria2.get("gidA")

        assert record is not None
        assert record.rename_intent is not None

    async def test_finalize_updates_mapping_and_clears_intent_atomically(
        self, tmp_path
    ):
        source = tmp_path / "old.mkv"
        source.write_bytes(b"data")
        intent = _rename_intent("old.mkv", "new.mkv", source)

        async with Database() as db:
            await db.aria2.set_rename_intent("gidA", intent)
            finalized = await db.aria2.finalize_rename_intent("gidA", intent)

            assert finalized is True
            assert await db.aria2.get_renamed_paths("gidA") == {"old.mkv": "new.mkv"}
            assert await db.aria2.get_rename_intent("gidA") is None
            record = await db.aria2.get("gidA")
            assert record is not None
            assert record.rename_intent is None

    async def test_finalize_rejects_stale_intent_without_mutating_mapping(
        self, tmp_path
    ):
        source = tmp_path / "old.mkv"
        source.write_bytes(b"data")
        persisted = _rename_intent("old.mkv", "new.mkv", source)
        stale = Aria2RenameIntent(
            old_path="old.mkv",
            new_path="other.mkv",
            st_dev=persisted.st_dev,
            st_ino=persisted.st_ino,
            st_size=persisted.st_size,
            st_mtime_ns=persisted.st_mtime_ns,
        )

        async with Database() as db:
            await db.aria2.set_rename_intent("gidA", persisted)
            finalized = await db.aria2.finalize_rename_intent("gidA", stale)

            assert finalized is False
            assert await db.aria2.get_renamed_paths("gidA") == {}
            assert await db.aria2.get_rename_intent("gidA") == persisted


# ---------------------------------------------------------------------------
# torrents_files: relative-path mapping
# ---------------------------------------------------------------------------


class TestTorrentsFiles:
    async def test_returns_paths_relative_to_dir(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "getFiles":
                return [
                    {"path": "/downloads/Show/Season 1/ep01.mkv", "length": "100"},
                    {"path": "/downloads/Show/Season 1/ep01.ass", "length": "1"},
                ]
            if method == "tellStatus":
                return {"dir": "/downloads/Show/Season 1"}
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            files = await aria2.torrents_files("gidA")

        assert files == [
            {"name": "ep01.mkv", "size": 100},
            {"name": "ep01.ass", "size": 1},
        ]

    async def test_returns_persisted_renamed_paths(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "getFiles":
                return [{"path": "/downloads/Show/Season 1/ep01.mkv", "length": "100"}]
            if method == "tellStatus":
                return {"dir": "/downloads/Show/Season 1"}
            return None

        async with Database() as db:
            await db.aria2.set_renamed_path("gidA", "ep01.mkv", "Show - 01.mkv")

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            files = await aria2.torrents_files("gidA")

        assert files == [{"name": "Show - 01.mkv", "size": 100}]

    async def test_query_failure_returns_empty_list(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(side_effect=Aria2ConnectionError("down"))
        ):
            files = await aria2.torrents_files("gidA")
        assert files == []


# ---------------------------------------------------------------------------
# torrents_rename_file: real filesystem move
# ---------------------------------------------------------------------------


class TestTorrentsRenameFile:
    async def test_renames_file_on_disk(self, tmp_path):
        aria2 = _aria2()
        (tmp_path / "old.mkv").write_bytes(b"data")

        async def fake_call(method, params=None, timeout=10.0):
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")

        assert result.outcome is RenameOutcome.RENAMED
        assert not (tmp_path / "old.mkv").exists()
        assert (tmp_path / "new.mkv").read_bytes() == b"data"

    async def test_rename_updates_torrents_files_path(self, tmp_path):
        aria2 = _aria2()
        old_file = tmp_path / "old.mkv"
        old_file.write_bytes(b"data")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "getFiles":
                return [{"path": str(old_file), "length": "4"}]
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")
            assert result.outcome is RenameOutcome.RENAMED
            files = await aria2.torrents_files("gidA")

        assert files == [{"name": "new.mkv", "size": 4}]

    async def test_chained_rename_keeps_original_aria2_path_in_sync(self, tmp_path):
        aria2 = _aria2()
        old_file = tmp_path / "old.mkv"
        old_file.write_bytes(b"data")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "getFiles":
                return [{"path": str(old_file), "length": "4"}]
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            first = await aria2.torrents_rename_file("gidA", "old.mkv", "mid.mkv")
            second = await aria2.torrents_rename_file("gidA", "mid.mkv", "new.mkv")
            assert first.outcome is RenameOutcome.RENAMED
            assert second.outcome is RenameOutcome.RENAMED
            files = await aria2.torrents_files("gidA")

        assert files == [{"name": "new.mkv", "size": 4}]

    async def test_creates_parent_dirs_for_nested_new_path(self, tmp_path):
        aria2 = _aria2()
        (tmp_path / "old.mkv").write_bytes(b"data")

        async def fake_call(method, params=None, timeout=10.0):
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file(
                "gidA", "old.mkv", os.path.join("Season 01", "new.mkv")
            )

        assert result.outcome is RenameOutcome.RENAMED
        assert (tmp_path / "Season 01" / "new.mkv").exists()

    async def test_returns_false_when_source_file_missing(self, tmp_path):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file("gidA", "missing.mkv", "new.mkv")

        assert result.outcome is RenameOutcome.RETRYABLE_FAILURE

    async def test_recovers_move_completed_before_sidecar_commit(self, tmp_path):
        aria2 = _aria2()
        old_file = tmp_path / "old.mkv"
        new_file = tmp_path / "new.mkv"
        old_file.write_bytes(b"data")
        intent = _rename_intent("old.mkv", "new.mkv", old_file)
        async with Database() as db:
            await db.aria2.set_rename_intent("gidA", intent)
        old_file.rename(new_file)

        async def fake_call(method, params=None, timeout=10.0):
            if method == "getFiles":
                return [{"path": str(tmp_path / "old.mkv"), "length": "4"}]
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")
            files = await aria2.torrents_files("gidA")

        assert result.outcome is RenameOutcome.ALREADY_APPLIED
        assert files == [{"name": "new.mkv", "size": 4}]
        async with Database() as db:
            record = await db.aria2.get("gidA")
            assert record is not None
            assert record.rename_intent is None

    async def test_missing_source_does_not_claim_unrelated_target_without_intent(
        self, tmp_path
    ):
        aria2 = _aria2()
        target = tmp_path / "new.mkv"
        target.write_bytes(b"unrelated")

        async def fake_call(method, params=None, timeout=10.0):
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")

        assert result.outcome is RenameOutcome.DESTINATION_EXISTS
        assert target.read_bytes() == b"unrelated"
        async with Database() as db:
            assert await db.aria2.get_renamed_paths("gidA") == {}

    async def test_crash_recovery_rejects_target_with_mismatched_fingerprint(
        self, tmp_path
    ):
        aria2 = _aria2()
        old_file = tmp_path / "old.mkv"
        old_file.write_bytes(b"original")
        intent = _rename_intent("old.mkv", "new.mkv", old_file)
        async with Database() as db:
            await db.aria2.set_rename_intent("gidA", intent)
        old_file.unlink()
        (tmp_path / "new.mkv").write_bytes(b"unrelated")

        async def fake_call(method, params=None, timeout=10.0):
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")

        assert result.outcome is RenameOutcome.DESTINATION_EXISTS
        async with Database() as db:
            record = await db.aria2.get("gidA")
            assert record is not None
            assert record.rename_intent is None
            assert await db.aria2.get_renamed_paths("gidA") == {}

    async def test_move_failure_clears_rename_intent(self, tmp_path):
        aria2 = _aria2()
        (tmp_path / "old.mkv").write_bytes(b"data")

        async def fake_call(method, params=None, timeout=10.0):
            return {"dir": str(tmp_path)}

        with (
            patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)),
            patch.object(aria2, "_move_file", side_effect=OSError("move failed")),
        ):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")

        assert result.outcome is RenameOutcome.RETRYABLE_FAILURE
        async with Database() as db:
            record = await db.aria2.get("gidA")
            assert record is not None
            assert record.rename_intent is None

    async def test_torrents_rename_file_existing_destination_refuses_overwrite(
        self, tmp_path
    ):
        """目标文件已存在时绝不覆盖（多文件电影种子可能映射到同一目标名）。"""
        aria2 = _aria2()
        (tmp_path / "old.mkv").write_bytes(b"source data")
        (tmp_path / "new.mkv").write_bytes(b"precious existing data")

        async def fake_call(method, params=None, timeout=10.0):
            return {"dir": str(tmp_path)}

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")

        assert result.outcome is RenameOutcome.DESTINATION_EXISTS
        # 两个文件都原封不动。
        assert (tmp_path / "old.mkv").read_bytes() == b"source data"
        assert (tmp_path / "new.mkv").read_bytes() == b"precious existing data"

    async def test_returns_false_when_status_lookup_fails(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(side_effect=Aria2ConnectionError("down"))
        ):
            result = await aria2.torrents_rename_file("gidA", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.RETRYABLE_FAILURE


# ---------------------------------------------------------------------------
# torrents_delete: filesystem cleanup that never touches sibling gids
# ---------------------------------------------------------------------------


class TestTorrentsDelete:
    async def test_deletes_only_this_gids_files_and_prunes_empty_subdir(self, tmp_path):
        aria2 = _aria2()
        season_dir = tmp_path / "Season 1"
        this_gid_dir = season_dir / "MyBatch"
        this_gid_dir.mkdir(parents=True)
        this_file = this_gid_dir / "ep01.mkv"
        this_file.write_bytes(b"data")
        sibling_file = season_dir / "ep02.mkv"
        sibling_file.write_bytes(b"other data")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"dir": str(season_dir)}
            if method == "getFiles":
                return [{"path": str(this_file)}]
            if method == "forceRemove":
                return "gidA"
            return None

        async with Database() as db:
            await db.aria2.upsert("gidA", bangumi_id=1)

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_delete("gidA", delete_files=True)

        assert result is True
        assert not this_file.exists()
        assert not this_gid_dir.exists()  # emptied subdirectory pruned
        assert sibling_file.exists()  # sibling never touched
        assert season_dir.exists()  # boundary directory never removed

        async with Database() as db:
            assert await db.aria2.get("gidA") is None

    async def test_returns_false_on_remove_rpc_error(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"dir": "/downloads"}
            if method == "getFiles":
                return []
            if method == "forceRemove":
                raise Aria2RpcError(1, "Internal error")
            return None

        async with Database() as db:
            await db.aria2.upsert(
                "gidA", bangumi_id=1, renamed_paths='{"old.mkv": "staged.mkv"}'
            )

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_delete("gidA", delete_files=False)

        assert result is False
        async with Database() as db:
            record = await db.aria2.get("gidA")
        assert record is not None
        assert record.renamed_paths == '{"old.mkv": "staged.mkv"}'

    async def test_delete_uses_current_renamed_path_not_reoccupied_original(
        self, tmp_path
    ):
        aria2 = _aria2()
        original = tmp_path / "Show S01E01.mkv"
        staged = tmp_path / ".Show S01E01.ab-old.mkv"
        staged.write_bytes(b"old-v1")
        original.write_bytes(b"new-v2")

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"dir": str(tmp_path)}
            if method == "getFiles":
                return [{"path": str(original)}]
            if method == "forceRemove":
                return "gidA"
            return None

        async with Database() as db:
            await db.aria2.upsert("gidA", bangumi_id=1)
            await db.aria2.set_renamed_path("gidA", original.name, staged.name)

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_delete("gidA", delete_files=True)

        assert result is True
        assert not staged.exists()
        assert original.read_bytes() == b"new-v2"
        async with Database() as db:
            assert await db.aria2.get("gidA") is None

    async def test_file_listing_failure_preserves_sidecar_and_task(self):
        aria2 = _aria2()
        calls = []

        async def fake_call(method, params=None, timeout=10.0):
            calls.append(method)
            if method == "tellStatus":
                return {"dir": "/downloads"}
            if method == "getFiles":
                raise Aria2ConnectionError("down")
            if method == "forceRemove":
                return "gidA"
            return None

        async with Database() as db:
            await db.aria2.upsert(
                "gidA", bangumi_id=1, renamed_paths='{"old.mkv": "staged.mkv"}'
            )

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_delete("gidA", delete_files=True)

        assert result is False
        assert "forceRemove" not in calls
        async with Database() as db:
            assert await db.aria2.get("gidA") is not None

    async def test_not_found_error_is_treated_as_already_gone(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"dir": "/downloads"}
            if method == "getFiles":
                return []
            if method == "forceRemove":
                raise Aria2RpcError(1, "GID#gidA is not found")
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_delete("gidA", delete_files=False)

        assert result is True

    async def test_not_found_before_file_listing_clears_stale_sidecar(self):
        aria2 = _aria2()

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                raise Aria2RpcError(1, "GID#gidA is not found")
            raise AssertionError(f"unexpected RPC after not-found: {method}")

        async with Database() as db:
            await db.aria2.upsert(
                "gidA", bangumi_id=1, renamed_paths='{"old.mkv": "staged.mkv"}'
            )

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            result = await aria2.torrents_delete("gidA", delete_files=True)

        assert result is True
        async with Database() as db:
            assert await db.aria2.get("gidA") is None

    async def test_accepts_pipe_joined_hashes(self):
        aria2 = _aria2()
        seen_gids = []

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"dir": "/downloads"}
            if method == "getFiles":
                return []
            if method == "forceRemove":
                seen_gids.append(params[0])
                return params[0]
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            await aria2.torrents_delete("gidA|gidB", delete_files=False)

        assert seen_gids == ["gidA", "gidB"]


# ---------------------------------------------------------------------------
# pause / resume
# ---------------------------------------------------------------------------


class TestPauseResume:
    async def test_pause_calls_force_pause_per_gid(self):
        aria2 = _aria2()
        call_mock = AsyncMock(return_value=None)
        with patch.object(aria2, "_call", call_mock):
            await aria2.torrents_pause(["gidA", "gidB"])
        methods = [c.args[0] for c in call_mock.call_args_list]
        assert methods == ["forcePause", "forcePause"]

    async def test_resume_calls_unpause_per_gid(self):
        aria2 = _aria2()
        call_mock = AsyncMock(return_value=None)
        with patch.object(aria2, "_call", call_mock):
            await aria2.torrents_resume("gidA|gidB")
        methods = [c.args[0] for c in call_mock.call_args_list]
        assert methods == ["unpause", "unpause"]

    async def test_pause_failure_is_logged_not_raised(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(side_effect=Aria2ConnectionError("down"))
        ):
            await aria2.torrents_pause("gidA")  # must not raise


# ---------------------------------------------------------------------------
# move_torrent
# ---------------------------------------------------------------------------


class TestMoveTorrent:
    async def test_moves_files_to_new_dir_and_updates_option(self, tmp_path):
        aria2 = _aria2()
        old_dir = tmp_path / "old"
        new_dir = tmp_path / "new"
        old_dir.mkdir()
        file_path = old_dir / "ep01.mkv"
        file_path.write_bytes(b"data")

        change_option_calls = []

        async def fake_call(method, params=None, timeout=10.0):
            if method == "tellStatus":
                return {"dir": str(old_dir)}
            if method == "getFiles":
                return [{"path": str(file_path)}]
            if method == "changeOption":
                change_option_calls.append(params)
                return "OK"
            return None

        with patch.object(aria2, "_call", AsyncMock(side_effect=fake_call)):
            await aria2.move_torrent("gidA", str(new_dir))

        assert not file_path.exists()
        assert (new_dir / "ep01.mkv").read_bytes() == b"data"
        assert change_option_calls == [["gidA", {"dir": str(new_dir)}]]

    async def test_skips_when_new_location_equals_current_dir(self, tmp_path):
        aria2 = _aria2()
        call_mock = AsyncMock(return_value={"dir": str(tmp_path)})
        with patch.object(aria2, "_call", call_mock):
            await aria2.move_torrent("gidA", str(tmp_path))
        # Only the tellStatus lookup ran -- no getFiles/changeOption follow-up.
        assert call_mock.call_args_list[-1].args[0] == "tellStatus"
        assert call_mock.call_count == 1


# ---------------------------------------------------------------------------
# set_category / add_tag
# ---------------------------------------------------------------------------


class TestSetCategoryAddTag:
    async def test_set_category_persists_to_sidecar(self):
        aria2 = _aria2()
        await aria2.set_category("gidA", "BangumiCollection")
        async with Database() as db:
            record = await db.aria2.get("gidA")
        assert record is not None
        assert record.category == "BangumiCollection"

    async def test_add_tag_parses_ab_prefix_and_persists_bangumi_id(self):
        aria2 = _aria2()
        await aria2.add_tag("gidA", "ab:99")
        async with Database() as db:
            record = await db.aria2.get("gidA")
        assert record is not None
        assert record.bangumi_id == 99

    async def test_add_tag_ignores_unsupported_tag(self):
        aria2 = _aria2()
        await aria2.add_tag("gidA", "some-other-tag")
        async with Database() as db:
            record = await db.aria2.get("gidA")
        assert record is None


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------


class TestCheckConnection:
    async def test_returns_version_string(self):
        aria2 = _aria2()
        with patch.object(
            aria2, "_call", AsyncMock(return_value={"version": "1.36.0"})
        ):
            result = await aria2.check_connection()
        assert result == "1.36.0"

    async def test_missing_version_field_returns_unknown(self):
        aria2 = _aria2()
        with patch.object(aria2, "_call", AsyncMock(return_value={})):
            result = await aria2.check_connection()
        assert result == "unknown"
