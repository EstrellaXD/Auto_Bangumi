"""Tests for QbDownloader: constructor, SSL/scheme logic, auth, and error handling.

The implementation keeps _use_https as a local variable computed inside auth()
from self.host, so SSL/HTTPS behaviour is validated by observing auth() side-effects
(log messages) rather than reading an instance attribute directly.
"""

import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

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
    assert qb.host.startswith(expected_prefix), (
        f"host={host!r} ssl={ssl} -> expected prefix {expected_prefix!r}, got {qb.host!r}"
    )


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

        captured_timeouts: list[httpx.Timeout] = []

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
        assert captured_timeouts[0].connect == pytest.approx(5.0)

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
        """Non-200 response returns False instead of silently succeeding."""
        qb = QbDownloader(host="localhost:8080", username="u", password="p", ssl=False)
        qb._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        qb._client.request = AsyncMock(return_value=mock_resp)

        result = await qb.torrents_delete("aaa", delete_files=True)

        assert result is False
