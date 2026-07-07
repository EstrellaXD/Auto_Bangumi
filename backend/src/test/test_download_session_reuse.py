"""Regression tests for qBittorrent session reuse (#1039 / #900).

The concrete client is cached across ``async with DownloadClient()`` blocks so
we log in once, re-authenticate only when the session expires, and rebuild when
connection settings change.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.downloader.client.qb_downloader import QbDownloader
from module.downloader.download_client import DownloadClient


def _patch_qb_settings(mock_settings, host="localhost:8080"):
    mock_settings.downloader.type = "qbittorrent"
    mock_settings.downloader.host = host
    mock_settings.downloader.username = "admin"
    mock_settings.downloader.password = "admin"
    mock_settings.downloader.ssl = False


class _FakeHTTP:
    """Minimal httpx.AsyncClient stand-in counting logins and data requests."""

    def __init__(self, login_calls: list, request_calls: list):
        self._login_calls = login_calls
        self._request_calls = request_calls

    async def post(self, url, data=None):
        # auth/login and auth/logout both arrive via post(); count logins only.
        if url.endswith("auth/login"):
            self._login_calls.append(url)
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "Ok."
        return resp

    async def request(self, method, url, **kwargs):
        self._request_calls.append((method, url))
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "Ok."
        resp.json = lambda: []
        return resp

    async def aclose(self):
        pass


class TestSessionReuse:
    async def test_two_blocks_share_one_login(self):
        """Two sequential ``async with DownloadClient()`` blocks log in once."""
        login_calls: list = []
        request_calls: list = []

        def make_http(*args, **kwargs):
            return _FakeHTTP(login_calls, request_calls)

        with patch("module.downloader.download_client.settings") as mock_settings:
            _patch_qb_settings(mock_settings)
            with patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                side_effect=make_http,
            ):
                async with DownloadClient():
                    pass
                async with DownloadClient():
                    pass

        assert len(login_calls) == 1

    async def test_expired_session_reauths_once_and_retries(self):
        """A 403 mid-operation forces exactly one re-login, then the op succeeds."""
        qb = QbDownloader("localhost:8080", "admin", "admin", ssl=False)
        login_calls: list = []
        request_calls: list = []

        class _Fake403Once:
            async def post(self, url, data=None):
                login_calls.append(url)
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def request(self, method, url, **kwargs):
                request_calls.append((method, url))
                resp = MagicMock()
                # First data request hits an expired session; retry succeeds.
                resp.status_code = 403 if len(request_calls) == 1 else 200
                resp.json = lambda: []
                return resp

            async def aclose(self):
                pass

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=_Fake403Once(),
        ):
            await qb.auth()
            resp = await qb._get("torrents/info")

        assert resp.status_code == 200
        assert len(login_calls) == 2  # initial login + one forced re-login
        assert len(request_calls) == 2  # original request + one retry

    async def test_settings_change_creates_new_client(self):
        """Changing the connection settings retires the cached client."""
        with patch("module.downloader.download_client.settings") as mock_settings:
            _patch_qb_settings(mock_settings, host="host-a:8080")
            first = DownloadClient().client
            reused = DownloadClient().client  # same settings -> same client
            _patch_qb_settings(mock_settings, host="host-b:8080")
            rebuilt = DownloadClient().client  # settings changed -> new client

        assert first is reused
        assert first is not rebuilt

    async def test_no_login_idempotency_on_cheap_reauth(self):
        """QbDownloader.auth() short-circuits when already authenticated."""
        qb = QbDownloader("localhost:8080", "admin", "admin", ssl=False)
        login_calls: list = []

        def make_http(*args, **kwargs):
            client = MagicMock()

            async def _post(url, data=None):
                login_calls.append(url)
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            client.post = _post
            client.aclose = AsyncMock()
            return client

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            side_effect=make_http,
        ):
            assert await qb.auth() is True
            assert await qb.auth() is True  # cheap, no second login

        assert len(login_calls) == 1

    async def test_concurrent_auth_calls_share_one_login(self):
        """并发的 auth()（重叠的 loop tick）必须单飞：只发一次 login POST，
        否则失败时并发登录会叠加计入 qB 的 WebUI IP ban 阈值。"""
        qb = QbDownloader("localhost:8080", "admin", "admin", ssl=False)
        login_calls: list = []

        class _SlowLogin:
            async def post(self, url, data=None):
                if url.endswith("auth/login"):
                    login_calls.append(url)
                    await asyncio.sleep(0.01)
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                pass

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=_SlowLogin(),
        ):
            r1, r2 = await asyncio.gather(qb.auth(), qb.auth())

        assert r1 is True and r2 is True
        assert len(login_calls) == 1


class _FakeRejectHTTP:
    """登录永远被拒（错误密码）的 httpx 替身。"""

    def __init__(self, login_calls: list):
        self._login_calls = login_calls

    async def post(self, url, data=None):
        if url.endswith("auth/login"):
            self._login_calls.append(url)
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "Fails."
        return resp

    async def aclose(self):
        pass


class TestCredentialFailureLatch:
    """凭据被拒后不得每个 tick 重试登录：约 5 次失败就会触发 qB 的 IP ban。"""

    async def test_bad_credentials_do_not_relogin_every_block(self):
        login_calls: list = []

        with patch("module.downloader.download_client.settings") as mock_settings:
            _patch_qb_settings(mock_settings)
            with patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                side_effect=lambda *a, **k: _FakeRejectHTTP(login_calls),
            ):
                for _ in range(3):  # 三个先后到来的 loop tick
                    with pytest.raises(ConnectionError):
                        async with DownloadClient():
                            pass

        assert len(login_calls) == 1

    async def test_concurrent_bad_credential_auths_send_one_login(self):
        """并发等待者不得在首个失败者确认"凭据被拒"后再各发一次 login POST。"""
        login_calls: list = []

        class _SlowReject:
            async def post(self, url, data=None):
                if url.endswith("auth/login"):
                    login_calls.append(url)
                    await asyncio.sleep(0.01)
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Fails."
                return resp

            async def aclose(self):
                pass

        qb = QbDownloader("localhost:8080", "admin", "wrong", ssl=False)
        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=_SlowReject(),
        ):
            r = await asyncio.gather(qb.auth(), qb.auth(), qb.auth())

        assert r == [False, False, False]
        assert len(login_calls) == 1

    async def test_latch_cleared_on_explicit_clear(self):
        """配置保存（reload_settings）后清除闩锁，允许重试一次登录。"""
        from module.downloader.download_client import clear_credential_latch

        login_calls: list = []

        with patch("module.downloader.download_client.settings") as mock_settings:
            _patch_qb_settings(mock_settings)
            with patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                side_effect=lambda *a, **k: _FakeRejectHTTP(login_calls),
            ):
                with pytest.raises(ConnectionError):
                    async with DownloadClient():
                        pass
                clear_credential_latch()
                with pytest.raises(ConnectionError):
                    async with DownloadClient():
                        pass

        assert len(login_calls) == 2


class TestRetiredClientLifecycle:
    async def test_two_rapid_settings_changes_close_both_retired_clients(self):
        """连续两次改设置（期间没有任何 enter）不得丢失第一个被撤下的
        客户端——它的连接池必须在下次 enter 时被关闭，而不是泄漏到进程结束。"""
        fakes: list = []

        class _TrackedHTTP:
            def __init__(self):
                self.closed = False
                fakes.append(self)

            async def post(self, url, data=None):
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                self.closed = True

        with patch("module.downloader.download_client.settings") as mock_settings:
            with patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                side_effect=lambda *a, **k: _TrackedHTTP(),
            ):
                _patch_qb_settings(mock_settings, host="host-a:8080")
                async with DownloadClient():
                    pass  # A 已认证，连接池已打开
                _patch_qb_settings(mock_settings, host="host-b:8080")
                DownloadClient()  # 撤下 A（未 enter）
                _patch_qb_settings(mock_settings, host="host-c:8080")
                DownloadClient()  # 撤下 B——不得把 A 顶掉忘掉
                async with DownloadClient():
                    pass

        assert fakes[0].closed is True  # A 的连接池被关闭，未泄漏

    async def test_cancelled_auth_releases_holder_bookkeeping(self):
        """__aenter__ 的 auth() 被取消/抛异常时必须释放引用计数，否则被撤下
        的客户端永远挂在 pending-close 上、连接池永不关闭。"""
        from module.downloader import download_client as dc

        class _HangingLogin:
            async def post(self, url, data=None):
                if url.endswith("auth/login"):
                    await asyncio.Event().wait()  # 永不返回，等着被取消
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                pass

        with patch("module.downloader.download_client.settings") as mock_settings:
            _patch_qb_settings(mock_settings)
            with patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                return_value=_HangingLogin(),
            ):

                async def enter_block():
                    async with DownloadClient():
                        pass

                task = asyncio.create_task(enter_block())
                await asyncio.sleep(0.01)  # 进入 auth() 等待
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task

        assert dc._active_holders == {}

    async def test_settings_change_does_not_close_client_mid_login(self):
        """设置变更时，另一个块还在 __aenter__ 的 auth() 中途（尚未计入
        引用计数）——不得把它正在登录的客户端关掉。"""
        events: list[str] = []
        login_started = asyncio.Event()
        release_login = asyncio.Event()

        class _SlowLoginHTTP:
            async def post(self, url, data=None):
                if url.endswith("auth/login"):
                    login_started.set()
                    await release_login.wait()
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                events.append("A-closed")

        class _FastHTTP:
            async def post(self, url, data=None):
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                pass

        with patch("module.downloader.download_client.settings") as mock_settings:
            with patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                side_effect=[_SlowLoginHTTP(), _FastHTTP()],
            ):
                _patch_qb_settings(mock_settings, host="host-a:8080")

                async def block1():
                    async with DownloadClient():
                        events.append("block1-in")
                    events.append("block1-out")

                task = asyncio.create_task(block1())
                await login_started.wait()  # block1 正在 auth() 中途

                _patch_qb_settings(mock_settings, host="host-b:8080")
                async with DownloadClient():  # 撤下 A 并触发关闭决策
                    pass

                release_login.set()
                await task

        assert "A-closed" in events
        # A 只能在 block1 成功 enter 之后关闭（由 block1 的 __aexit__ 收尾），
        # 不得在其登录中途被关。
        assert events.index("A-closed") > events.index("block1-in")
