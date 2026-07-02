"""Regression tests for qBittorrent session reuse (#1039 / #900).

The concrete client is cached across ``async with DownloadClient()`` blocks so
we log in once, re-authenticate only when the session expires, and rebuild when
connection settings change.
"""

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
