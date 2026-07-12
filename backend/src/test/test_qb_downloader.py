"""Tests for QbDownloader: constructor, SSL/scheme logic, auth, and error handling.

The implementation keeps _use_https as a local variable computed inside auth()
from self.host, so SSL/HTTPS behaviour is validated by observing auth() side-effects
(log messages) rather than reading an instance attribute directly.
"""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from module.downloader import AddResult, RenameOutcome
from module.downloader.client.qb_downloader import QbDownloader

# ---------------------------------------------------------------------------
# Constructor / URL building
# ---------------------------------------------------------------------------


class TestQbDownloaderConstructor:
    """Verify host URL normalisation at construction time."""

    def test_ssl_true_no_scheme_uses_https(self):
        """ssl=True with bare host prepends https://."""
        qb = QbDownloader(
            host="192.168.1.10:8080", username="admin", password="pass", ssl=True
        )
        assert qb.host == "https://192.168.1.10:8080"

    def test_ssl_false_no_scheme_uses_http(self):
        """ssl=False with bare host prepends http://."""
        qb = QbDownloader(
            host="192.168.1.10:8080", username="admin", password="pass", ssl=False
        )
        assert qb.host == "http://192.168.1.10:8080"

    def test_explicit_http_scheme_preserved_when_ssl_true(self):
        """Explicit http:// scheme is kept even if ssl=True."""
        qb = QbDownloader(
            host="http://192.168.1.10:8080", username="admin", password="pass", ssl=True
        )
        assert qb.host == "http://192.168.1.10:8080"

    def test_explicit_https_scheme_preserved_when_ssl_false(self):
        """Explicit https:// scheme is kept even if ssl=False."""
        qb = QbDownloader(
            host="https://192.168.1.10:8080",
            username="admin",
            password="pass",
            ssl=False,
        )
        assert qb.host == "https://192.168.1.10:8080"

    def test_explicit_http_scheme_preserved_ssl_false(self):
        """Explicit http:// URL with ssl=False stays as http://."""
        qb = QbDownloader(
            host="http://nas.local:8080", username="u", password="p", ssl=False
        )
        assert qb.host == "http://nas.local:8080"

    def test_explicit_https_scheme_preserved_ssl_true(self):
        """Explicit https:// URL with ssl=True stays as https://."""
        qb = QbDownloader(
            host="https://nas.local:8080", username="u", password="p", ssl=True
        )
        assert qb.host == "https://nas.local:8080"

    def test_credentials_stored(self):
        """Constructor stores username, password, and ssl flag as-is."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="secret", ssl=False
        )
        assert qb.username == "admin"
        assert qb.password == "secret"
        assert qb.ssl is False

    def test_client_initially_none(self):
        """_client starts as None before any auth call."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )
        assert qb._client is None


# ---------------------------------------------------------------------------
# Scheme selection: parametrised matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host,ssl,expected_prefix",
    [
        # Bare host - scheme derived from ssl flag
        ("192.168.1.1:8080", True, "https://"),
        ("192.168.1.1:8080", False, "http://"),
        ("qb.home", True, "https://"),
        ("qb.home", False, "http://"),
        # Explicit http:// always wins regardless of ssl
        ("http://192.168.1.1:8080", True, "http://"),
        ("http://192.168.1.1:8080", False, "http://"),
        # Explicit https:// always wins regardless of ssl
        ("https://192.168.1.1:8080", True, "https://"),
        ("https://192.168.1.1:8080", False, "https://"),
    ],
)
def test_scheme_selection_matrix(host: str, ssl: bool, expected_prefix: str):
    """Constructor resolves host scheme correctly for all input combinations."""
    qb = QbDownloader(host=host, username="u", password="p", ssl=ssl)
    assert qb.host.startswith(
        expected_prefix
    ), f"host={host!r} ssl={ssl} -> expected prefix {expected_prefix!r}, got {qb.host!r}"


# ---------------------------------------------------------------------------
# auth: AsyncClient is created with verify=False
# ---------------------------------------------------------------------------


class TestAuthClientCreation:
    """auth() must create the httpx.AsyncClient with verify=False unconditionally."""

    async def test_auth_creates_client_with_verify_false_when_ssl_true(self):
        """verify=False is used even when ssl=True (self-signed certs are common)."""
        qb = QbDownloader(
            host="192.168.1.10:8080", username="admin", password="pass", ssl=True
        )

        captured: list[dict] = []

        class _FakeClient:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            async def post(self, url, data=None):
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                pass

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient", _FakeClient
        ):
            result = await qb.auth()

        assert result is True
        assert len(captured) == 1
        assert captured[0].get("verify") is False

    async def test_auth_creates_client_with_verify_false_when_ssl_false(self):
        """verify=False is used even when ssl=False."""
        qb = QbDownloader(
            host="192.168.1.10:8080", username="admin", password="pass", ssl=False
        )

        captured: list[dict] = []

        class _FakeClient:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            async def post(self, url, data=None):
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                pass

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient", _FakeClient
        ):
            result = await qb.auth()

        assert result is True
        assert captured[0].get("verify") is False

    async def test_auth_uses_5_second_connect_timeout(self):
        """auth() sets connect timeout to 5.0 seconds."""
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)

        captured_timeouts: list[httpx.Timeout | None] = []

        class _FakeClient:
            def __init__(self, **kwargs):
                captured_timeouts.append(kwargs.get("timeout"))

            async def post(self, url, data=None):
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                pass

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient", _FakeClient
        ):
            await qb.auth()

        assert len(captured_timeouts) == 1
        timeout = captured_timeouts[0]
        assert timeout is not None
        assert timeout.connect == pytest.approx(5.0)

    async def test_auth_sets_connection_limits_for_keepalive(self):
        """Regression for #984: qB client must cap keepalive so idle TCP
        sockets don't linger past proxy / NAS idle-reap timeouts, otherwise
        parallel renamer calls cascade into 'Server disconnected' errors."""
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)

        captured: list[dict] = []

        class _FakeClient:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            async def post(self, url, data=None):
                resp = MagicMock()
                resp.status_code = 200
                resp.text = "Ok."
                return resp

            async def aclose(self):
                pass

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient", _FakeClient
        ):
            await qb.auth()

        limits = captured[0].get("limits")
        assert limits is not None
        assert limits.keepalive_expiry is not None
        assert limits.keepalive_expiry > 0
        assert limits.max_connections is not None


# ---------------------------------------------------------------------------
# auth: success / failure paths
# ---------------------------------------------------------------------------


class TestAuthSuccessFailure:
    """auth() return value reflects qBittorrent server responses."""

    async def test_auth_returns_true_on_ok_response(self):
        """Returns True when server responds 200 + 'Ok.'."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Ok."
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await qb.auth()

        assert result is True

    async def test_auth_returns_false_on_403(self):
        """Returns False and stops retrying immediately on 403 Forbidden."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await qb.auth(retry=3)

        assert result is False
        # Should break immediately on 403, not exhaust all retries
        assert mock_client.post.call_count == 1

    async def test_auth_retries_up_to_limit_on_server_error(self):
        """Retries up to the retry limit on non-200/non-403 responses."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await qb.auth(retry=2)

        assert result is False
        assert mock_client.post.call_count == 2


# ---------------------------------------------------------------------------
# auth: ConnectError logging - HTTPS vs HTTP message branching
# ---------------------------------------------------------------------------


class TestAuthConnectErrorLogging:
    """On ConnectError, the log message depends on whether the URL uses https://."""

    async def test_https_url_logs_https_specific_guidance(self, caplog):
        """HTTPS-specific guidance is logged when host uses https:// and ConnectError occurs."""
        # Use explicit https:// URL so the local use_https flag is True
        qb = QbDownloader(
            host="https://192.168.1.10:8080", username="u", password="p", ssl=True
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with caplog.at_level(
                    logging.ERROR, logger="module.downloader.client.qb_downloader"
                ):
                    result = await qb.auth(retry=1)

        assert result is False
        error_messages = [
            r.message for r in caplog.records if r.levelno == logging.ERROR
        ]
        assert any("HTTPS" in msg for msg in error_messages)
        assert any(
            "disable SSL" in msg or "plain HTTP" in msg for msg in error_messages
        )

    async def test_https_url_derived_from_ssl_flag_logs_https_guidance(self, caplog):
        """HTTPS guidance also fires when scheme comes from ssl=True (bare host)."""
        # Bare host + ssl=True -> self.host becomes https://... -> use_https=True in auth()
        qb = QbDownloader(
            host="192.168.1.10:8080", username="u", password="p", ssl=True
        )
        assert qb.host.startswith("https://")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with caplog.at_level(
                    logging.ERROR, logger="module.downloader.client.qb_downloader"
                ):
                    await qb.auth(retry=1)

        error_messages = [
            r.message for r in caplog.records if r.levelno == logging.ERROR
        ]
        assert any("HTTPS" in msg for msg in error_messages)

    async def test_http_url_logs_generic_message_without_ssl_hint(self, caplog):
        """Generic connection error is logged when host uses http:// and ConnectError occurs."""
        qb = QbDownloader(
            host="http://192.168.1.10:8080", username="u", password="p", ssl=False
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with caplog.at_level(
                    logging.ERROR, logger="module.downloader.client.qb_downloader"
                ):
                    result = await qb.auth(retry=1)

        assert result is False
        error_messages = [
            r.message for r in caplog.records if r.levelno == logging.ERROR
        ]
        assert any(
            "Cannot connect to qBittorrent Server" in msg for msg in error_messages
        )
        # SSL-disable hint must NOT appear for plain HTTP connections
        assert not any("disable SSL" in msg for msg in error_messages)

    async def test_http_url_derived_from_ssl_flag_false_no_ssl_hint(self, caplog):
        """SSL-disable hint is absent when scheme comes from ssl=False (bare host)."""
        qb = QbDownloader(
            host="192.168.1.10:8080", username="u", password="p", ssl=False
        )
        assert qb.host.startswith("http://")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with caplog.at_level(
                    logging.ERROR, logger="module.downloader.client.qb_downloader"
                ):
                    await qb.auth(retry=1)

        all_messages = " ".join(r.message for r in caplog.records)
        assert "disable SSL" not in all_messages
        assert "plain HTTP" not in all_messages

    async def test_connect_error_logs_check_ip_port_info(self, caplog):
        """Both HTTPS and HTTP paths log an info message about checking IP/port."""
        qb = QbDownloader(
            host="https://192.168.1.10:8080", username="u", password="p", ssl=True
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with caplog.at_level(
                    logging.INFO, logger="module.downloader.client.qb_downloader"
                ):
                    await qb.auth(retry=1)

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("IP" in msg or "port" in msg for msg in info_messages)

    async def test_explicit_http_with_ssl_true_still_uses_generic_message(self, caplog):
        """Explicit http:// URL overrides ssl=True: generic error message, no HTTPS hint."""
        # ssl=True but explicit http:// -> use_https=False inside auth()
        qb = QbDownloader(
            host="http://192.168.1.10:8080", username="u", password="p", ssl=True
        )
        assert qb.host.startswith("http://")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with caplog.at_level(
                    logging.ERROR, logger="module.downloader.client.qb_downloader"
                ):
                    await qb.auth(retry=1)

        error_messages = [
            r.message for r in caplog.records if r.levelno == logging.ERROR
        ]
        assert not any("disable SSL" in msg for msg in error_messages)
        assert not any("HTTPS" in msg for msg in error_messages)


# ---------------------------------------------------------------------------
# _url helper
# ---------------------------------------------------------------------------


class TestUrlHelper:
    """_url() builds the correct API endpoint path."""

    def test_url_format_with_http(self):
        """_url returns host + /api/v2/ + endpoint for http hosts."""
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        assert qb._url("auth/login") == "http://localhost:8080/api/v2/auth/login"

    def test_url_format_with_https(self):
        """_url includes https:// when SSL is used."""
        qb = QbDownloader(host="nas.local:8080", username="u", password="p", ssl=True)
        assert qb._url("app/version") == "https://nas.local:8080/api/v2/app/version"

    def test_url_with_explicit_http_scheme_overriding_ssl_true(self):
        """_url works correctly when explicit http:// scheme overrides ssl=True."""
        qb = QbDownloader(
            host="http://nas.local:8080", username="u", password="p", ssl=True
        )
        assert qb._url("torrents/info") == "http://nas.local:8080/api/v2/torrents/info"


# ---------------------------------------------------------------------------
# qBittorrent 5.2 login compatibility (#1044, #1034, #1043)
# ---------------------------------------------------------------------------


class TestAuthQb52Compat:
    """qBittorrent >= 5.2 returns HTTP 204 with an empty body on success."""

    async def test_auth_returns_true_on_204_empty_body(self):
        """Returns True when server responds 204 + empty body (qB >= 5.2)."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.text = ""
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await qb.auth()

        assert result is True

    async def test_auth_returns_false_on_200_fails_body(self):
        """Returns False on 200 + 'Fails.' (bad credentials, qB < 5.2)."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="wrong", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Fails."
        mock_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await qb.auth(retry=1)

        assert result is False

    async def test_auth_sets_last_auth_error_credentials_on_fails_body(self):
        """密码错误后 last_auth_error 标记为 credentials，供上层区分故障类型。"""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="wrong", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Fails."
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await qb.auth(retry=3)

        assert qb.last_auth_error == "credentials"

    async def test_auth_sets_last_auth_error_banned_on_403(self):
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await qb.auth(retry=3)

        assert qb.last_auth_error == "banned"

    async def test_auth_sets_last_auth_error_unreachable_on_connect_error(self):
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("boom"))

        with (
            patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            await qb.auth(retry=1)

        assert qb.last_auth_error == "unreachable"

    async def test_auth_clears_last_auth_error_on_success(self):
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )
        qb.last_auth_error = "credentials"

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Ok."
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await qb.auth()

        assert result is True
        assert qb.last_auth_error is None

    async def test_auth_stops_immediately_on_200_fails_body(self, caplog):
        """Wrong credentials (200 + 'Fails.') must not be retried — repeated
        failed logins trigger qBittorrent's WebUI IP ban — and the log must
        say the credentials are wrong."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="wrong", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Fails."
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await qb.auth(retry=3)

        assert result is False
        assert mock_client.post.call_count == 1
        assert "username or password" in caplog.text

    async def test_auth_stops_immediately_on_401(self, caplog):
        """401 also means bad credentials; same no-retry behaviour."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="wrong", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = ""
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch(
            "module.downloader.client.qb_downloader.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await qb.auth(retry=3)

        assert result is False
        assert mock_client.post.call_count == 1
        assert "username or password" in caplog.text

    async def test_auth_returns_false_on_200_html_body(self):
        """A 200 + HTML page (proxy, wrong service) is not a successful login."""
        qb = QbDownloader(
            host="localhost:8080", username="admin", password="pass", ssl=False
        )

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>Sign in</body></html>"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch(
                "module.downloader.client.qb_downloader.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "module.downloader.client.qb_downloader.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            result = await qb.auth(retry=1)

        assert result is False


# ---------------------------------------------------------------------------
# add_torrents
# ---------------------------------------------------------------------------


class TestAddTorrents:
    async def test_add_returns_added_on_ok_body(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=200, text="Ok.")
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:abc",
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.ADDED

    async def test_add_fails_body_with_existing_magnet_is_duplicate(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        btih = "a" * 40
        add_resp = MagicMock(status_code=200, text="Fails.")
        info_resp = MagicMock(status_code=200)
        info_resp.json.return_value = [{"hash": btih}]
        qb._client.request = AsyncMock(side_effect=[add_resp, info_resp])

        result = await qb.add_torrents(
            torrent_urls=f"magnet:?xt=urn:btih:{btih}",
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        # 磁力 hash 已存在于 qB：确认是重复
        assert result is AddResult.DUPLICATE

    async def test_add_fails_body_with_existing_torrent_file_is_duplicate(self):
        """qB ≤5.1 对 .torrent 文件上传回 'Fails.' 时，用文件字节算 infohash
        并到 qB 里确认——已存在即重复，不能永远按失败重试（用户日志里的
        '200 Fails. and no matching torrent found' 无限循环）。"""
        import hashlib

        raw = (
            b"d4:infod6:lengthi1e4:name3:foo12:piece lengthi16384e6:pieces20:"
            + b"\x00" * 20
            + b"ee"
        )
        infohash = hashlib.sha1(raw[7:-1]).hexdigest()

        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        add_resp = MagicMock(status_code=200, text="Fails.")
        info_resp = MagicMock(status_code=200)
        info_resp.json.return_value = [{"hash": infohash}]
        qb._client.request = AsyncMock(side_effect=[add_resp, info_resp])

        result = await qb.add_torrents(
            torrent_urls=None,
            torrent_files=raw,
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.DUPLICATE

    async def test_add_fails_body_with_unknown_torrent_file_raises(self):
        """文件 hash 不在 qB 中（真失败，如种子损坏）时仍按失败抛出。"""
        raw = (
            b"d4:infod6:lengthi1e4:name3:foo12:piece lengthi16384e6:pieces20:"
            + b"\x00" * 20
            + b"ee"
        )
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        add_resp = MagicMock(status_code=200, text="Fails.")
        info_resp = MagicMock(status_code=200)
        info_resp.json.return_value = []
        qb._client.request = AsyncMock(side_effect=[add_resp, info_resp])

        with pytest.raises(ConnectionError):
            await qb.add_torrents(
                torrent_urls=None,
                torrent_files=raw,
                save_path="/downloads",
                category="Bangumi",
            )

    def test_torrent_infohash_extraction(self):
        """infohash = bencoded info 字典的 SHA-1；损坏输入返回 None。"""
        import hashlib

        announce = b"http://tracker.example/announce"
        raw = (
            b"d8:announce"
            + str(len(announce)).encode()
            + b":"
            + announce
            + b"4:infod6:lengthi1e4:name3:foo12:piece lengthi16384e6:pieces20:"
            + b"\x01" * 20
            + b"ee"
        )
        info_start = raw.index(b"4:info") + len(b"4:info")
        expected = hashlib.sha1(raw[info_start:-1]).hexdigest()

        from module.downloader.client.qb_downloader import _torrent_infohash

        assert _torrent_infohash(raw) == expected
        assert _torrent_infohash(b"not a torrent") is None
        assert _torrent_infohash(b"d4:infoi3e") is None  # truncated/no dict end

    async def test_add_fails_body_without_confirmed_duplicate_raises(self):
        # "Fails." 也可能是种子损坏/无法解析——无法确认重复时必须按失败抛出，
        # 让上层保留重试机会，而不是记成已下载
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=200, text="Fails.")
        qb._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(ConnectionError):
            await qb.add_torrents(
                torrent_urls="https://mikanani.me/Download/broken.torrent",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

    async def test_add_raises_on_non_ok_status(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=415, text="Unsupported Media Type")
        qb._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(ConnectionError):
            await qb.add_torrents(
                torrent_urls="magnet:?xt=urn:btih:abc",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

    async def test_add_returns_added_on_json_success_body(self):
        # qBittorrent >= 5.2 返回逐种子 JSON 结果而非 "Ok."
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        body = (
            '{"added_torrent_ids":["5fab7547cd1f626f56a0b5492cfd25d60d0635c6"],'
            '"failure_count":0,"pending_count":0,"success_count":1}'
        )
        mock_resp = MagicMock(status_code=200, text=body)
        mock_resp.json.return_value = json.loads(body)
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:abc",
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.ADDED

    async def test_add_returns_added_on_202_json_pending_body(self):
        # URL 形式的 add 是异步下载：qB 5.2 回 202 + pending_count>0——
        # 已受理，同样视为成功
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        body = (
            '{"added_torrent_ids":[],'
            '"failure_count":0,"pending_count":1,"success_count":0}'
        )
        mock_resp = MagicMock(status_code=202, text=body)
        mock_resp.json.return_value = json.loads(body)
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:abc",
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.ADDED

    async def test_add_json_body_with_failures_and_existing_magnet_is_duplicate(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        btih = "a" * 40
        body = (
            '{"added_torrent_ids":[],'
            '"failure_count":1,"pending_count":0,"success_count":0}'
        )
        add_resp = MagicMock(status_code=200, text=body)
        add_resp.json.return_value = json.loads(body)
        info_resp = MagicMock(status_code=200)
        info_resp.json.return_value = [{"hash": btih}]
        qb._client.request = AsyncMock(side_effect=[add_resp, info_resp])

        result = await qb.add_torrents(
            torrent_urls=f"magnet:?xt=urn:btih:{btih}",
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.DUPLICATE

    async def test_add_json_body_with_failures_without_confirmed_duplicate_raises(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        body = (
            '{"added_torrent_ids":[],'
            '"failure_count":1,"pending_count":0,"success_count":0}'
        )
        mock_resp = MagicMock(status_code=200, text=body)
        mock_resp.json.return_value = json.loads(body)
        qb._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(ConnectionError):
            await qb.add_torrents(
                torrent_urls="https://mikanani.me/Download/broken.torrent",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

    async def test_add_409_with_torrent_file_is_duplicate(self):
        # qBittorrent >= 5.2 对已存在的种子回 409 Conflict (qbittorrent#18361)。
        # 文件上传是同步解析的：损坏文件走 415，所以文件的 409 就是重复。
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=409, text="Conflict")
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.add_torrents(
            torrent_urls=None,
            torrent_files=b"fake torrent bytes",
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.DUPLICATE

    async def test_add_409_with_existing_magnet_is_duplicate(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        btih = "b" * 40
        add_resp = MagicMock(status_code=409, text="Conflict")
        info_resp = MagicMock(status_code=200)
        info_resp.json.return_value = [{"hash": btih}]
        qb._client.request = AsyncMock(side_effect=[add_resp, info_resp])

        result = await qb.add_torrents(
            torrent_urls=f"magnet:?xt=urn:btih:{btih}",
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.DUPLICATE

    async def test_add_409_with_unconfirmed_url_raises(self):
        # URL 形式在 5.2 走异步（202），几乎不会 409；真出现且无法用 hash
        # 确认时按失败抛出，避免把损坏的 add 记成已下载
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=409, text="Conflict")
        qb._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(ConnectionError):
            await qb.add_torrents(
                torrent_urls="https://mikanani.me/Download/unknown.torrent",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

    async def test_add_json_partial_success_is_added(self):
        # 批量投递部分成功：与旧版 "Ok."（>=1 成功即 Ok.）和 aria2 客户端
        # 的约定一致，按 ADDED 处理，不能把整批记成失败
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        body = (
            '{"added_torrent_ids":["c" ],'
            '"failure_count":1,"pending_count":0,"success_count":1}'
        )
        mock_resp = MagicMock(status_code=200, text=body)
        mock_resp.json.return_value = json.loads(body)
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.add_torrents(
            torrent_urls=["magnet:?xt=urn:btih:abc", "magnet:?xt=urn:btih:def"],
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        assert result is AddResult.ADDED

    async def test_add_json_all_zero_counts_raises(self):
        # 三个计数全 0：什么都没加进去，不能算 ADDED
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        body = (
            '{"added_torrent_ids":[],'
            '"failure_count":0,"pending_count":0,"success_count":0}'
        )
        mock_resp = MagicMock(status_code=200, text=body)
        mock_resp.json.return_value = json.loads(body)
        qb._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(ConnectionError):
            await qb.add_torrents(
                torrent_urls="https://mikanani.me/Download/ignored.torrent",
                torrent_files=None,
                save_path="/downloads",
                category="Bangumi",
            )

    async def test_add_sends_both_paused_and_stopped_params(self):
        # qB 5.0 把 add 的 paused 参数改名为 stopped，双方都会静默忽略
        # 未知参数——必须两个都发才能覆盖所有版本
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=200, text="Ok.")
        qb._client.request = AsyncMock(return_value=mock_resp)

        await qb.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:abc",
            torrent_files=None,
            save_path="/downloads",
            category="Bangumi",
        )

        sent = qb._client.request.call_args.kwargs["data"]
        assert sent["paused"] == "false"
        assert sent["stopped"] == "false"


# ---------------------------------------------------------------------------
# torrents/pause|resume vs torrents/stop|start (qB 5.0 rename, no aliases)
# ---------------------------------------------------------------------------


class TestPauseResumeCompat:
    """qB 5.0 把 pause/resume 改名为 stop/start 且旧名 404；4.x 没有新名。
    客户端先试新名，404 时回退旧名并记住选择。"""

    async def test_pause_uses_stop_endpoint_first(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=200)
        qb._client.request = AsyncMock(return_value=mock_resp)

        await qb.torrents_pause("h1")

        url = qb._client.request.call_args.args[1]
        assert url.endswith("torrents/stop")

    async def test_pause_falls_back_to_legacy_endpoint_on_404(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        resp_404 = MagicMock(status_code=404)
        resp_200 = MagicMock(status_code=200)
        qb._client.request = AsyncMock(side_effect=[resp_404, resp_200])

        await qb.torrents_pause("h1")

        urls = [c.args[1] for c in qb._client.request.call_args_list]
        assert urls[0].endswith("torrents/stop")
        assert urls[1].endswith("torrents/pause")

    async def test_resume_remembers_legacy_era_after_fallback(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        resp_404 = MagicMock(status_code=404)
        resp_200 = MagicMock(status_code=200)
        qb._client.request = AsyncMock(side_effect=[resp_404, resp_200])
        await qb.torrents_pause("h1")

        qb._client.request = AsyncMock(return_value=MagicMock(status_code=200))
        await qb.torrents_resume("h1")

        url = qb._client.request.call_args.args[1]
        assert url.endswith("torrents/resume")

    async def test_resume_remembers_modern_era_after_success(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        qb._client.request = AsyncMock(return_value=MagicMock(status_code=200))
        await qb.torrents_pause("h1")

        await qb.torrents_resume("h1")

        url = qb._client.request.call_args.args[1]
        assert url.endswith("torrents/start")


# ---------------------------------------------------------------------------
# torrents/info filter=paused (qB 5.0 renamed the value; unknown value = All)
# ---------------------------------------------------------------------------


class TestTorrentsInfoPausedFilter:
    async def test_paused_filter_is_applied_client_side(self):
        # 5.x 把 filter=paused 改名 stopped，且未知 filter 值静默等于 All——
        # 服务端过滤不可跨版本，改为不带 filter 拉取后按 state 本地过滤
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = [
            {"hash": "a", "state": "pausedDL"},
            {"hash": "b", "state": "stoppedUP"},
            {"hash": "c", "state": "downloading"},
        ]
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.torrents_info(status_filter="paused", category="Bangumi")

        sent_params = qb._client.request.call_args.kwargs["params"]
        assert "filter" not in sent_params
        assert [t["hash"] for t in result] == ["a", "b"]

    async def test_completed_filter_still_server_side(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = []
        qb._client.request = AsyncMock(return_value=mock_resp)

        await qb.torrents_info(status_filter="completed", category="Bangumi")

        sent_params = qb._client.request.call_args.kwargs["params"]
        assert sent_params["filter"] == "completed"


class TestTorrentExists:
    async def test_queries_exact_hash_and_confirms_presence(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        response = MagicMock(status_code=200)
        response.json.return_value = [{"hash": "ABC123"}]
        qb._client.request = AsyncMock(return_value=response)

        assert await qb.torrent_exists("abc123") is True
        assert qb._client.request.call_args.kwargs["params"] == {"hashes": "abc123"}

    async def test_empty_exact_hash_query_confirms_absence(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        response = MagicMock(status_code=200)
        response.json.return_value = []
        qb._client.request = AsyncMock(return_value=response)

        assert await qb.torrent_exists("missing") is False

    async def test_failed_query_is_unknown_not_absent(self):
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        qb._client.request = AsyncMock(side_effect=ConnectionError("offline"))

        assert await qb.torrent_exists("abc123") is None


# ---------------------------------------------------------------------------
# torrents_delete (#1046)
# ---------------------------------------------------------------------------


class TestTorrentsDelete:
    """torrents_delete must pipe-join hash lists and report failures."""

    async def test_delete_joins_hash_list_with_pipe(self):
        """A list of hashes is sent as a single pipe-joined string."""
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Data ops now go through _request -> _client.request (session reuse).
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.torrents_delete(["aaa", "bbb"], delete_files=True)

        assert result is True
        sent = qb._client.request.call_args.kwargs["data"]
        assert sent["hashes"] == "aaa|bbb"
        assert sent["deleteFiles"] == "true"

    async def test_delete_returns_false_on_error_status(self):
        """Error response returns False instead of silently succeeding."""
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.torrents_delete("aaa", delete_files=True)

        assert result is False

    async def test_delete_accepts_204_empty_body(self):
        """qB 5.2 回 204 表示成功（空响应体全局改为 204）。"""
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.torrents_delete("aaa", delete_files=True)

        assert result is True


# ---------------------------------------------------------------------------
# torrents_rename_file verify contract (#754 / #749, from PR #1037)
# ---------------------------------------------------------------------------


class TestRenameVerifyContract:
    """Pin the verify contract: only trust a rename when new_path appears.

    qBittorrent can answer 200 without actually renaming (e.g. while seeding,
    or when the target name is taken by a duplicate from another source).
    Any false True here re-triggers rename + notification every rename cycle.
    """

    def _make_qb(self, file_list, post_code: int = 200):
        qb = QbDownloader(host="http://qb", username="u", password="p", ssl=False)
        qb._post = AsyncMock(return_value=MagicMock(status_code=post_code))
        qb.torrents_files = AsyncMock(return_value=file_list)
        return qb

    async def test_verify_false_when_file_keeps_old_name(self):
        """API 200 but the file never gets renamed -> retryable."""
        qb = self._make_qb([{"name": "old.mkv"}])
        result = await qb.torrents_rename_file("h", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.RETRYABLE_FAILURE

    async def test_verify_false_when_neither_name_present(self):
        """Neither old nor new name is retryable, not a blind success."""
        qb = self._make_qb([{"name": "unrelated.mkv"}])
        result = await qb.torrents_rename_file("h", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.RETRYABLE_FAILURE

    async def test_verify_true_when_new_path_appears(self):
        """A real, verified rename returns True."""
        qb = self._make_qb([{"name": "new.mkv"}])
        result = await qb.torrents_rename_file("h", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.RENAMED

    async def test_verify_409_conflict_is_false(self):
        """Target already exists is a terminal, distinguishable outcome."""
        qb = self._make_qb([{"name": "old.mkv"}], post_code=409)
        result = await qb.torrents_rename_file("h", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.DESTINATION_EXISTS

    async def test_rename_204_with_verified_new_path_is_true(self):
        """qB 5.2 对成功的 renameFile 回 204；不能再用 ==200 判定失败。"""
        qb = self._make_qb([{"name": "new.mkv"}], post_code=204)
        result = await qb.torrents_rename_file("h", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.RENAMED

    async def test_http_error_is_retryable(self):
        qb = self._make_qb([{"name": "old.mkv"}], post_code=500)
        result = await qb.torrents_rename_file("h", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.RETRYABLE_FAILURE

    async def test_network_error_is_retryable(self):
        qb = self._make_qb([])
        qb._post = AsyncMock(side_effect=httpx.ConnectError("down"))
        result = await qb.torrents_rename_file("h", "old.mkv", "new.mkv")
        assert result.outcome is RenameOutcome.RETRYABLE_FAILURE
