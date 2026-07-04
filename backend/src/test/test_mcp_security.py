"""Tests for module.mcp.security - McpAccessMiddleware, _is_allowed(), and clear_network_cache()."""

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from module.mcp.security import McpAccessMiddleware, _is_allowed, clear_network_cache

# ---------------------------------------------------------------------------
# _is_allowed() unit tests
# ---------------------------------------------------------------------------


class TestIsAllowed:
    """Verify _is_allowed() checks IPs against a given whitelist."""

    def setup_method(self):
        clear_network_cache()

    LOCAL_WHITELIST = [
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "::1/128",
        "fe80::/10",
        "fc00::/7",
    ]

    # --- allowed IPs ---

    def test_ipv4_loopback_allowed(self):
        assert _is_allowed("127.0.0.1", self.LOCAL_WHITELIST) is True

    def test_ipv4_loopback_range(self):
        assert _is_allowed("127.255.255.255", self.LOCAL_WHITELIST) is True

    def test_ipv4_10_network(self):
        assert _is_allowed("10.0.0.1", self.LOCAL_WHITELIST) is True

    def test_ipv4_172_16_network(self):
        assert _is_allowed("172.16.0.1", self.LOCAL_WHITELIST) is True

    def test_ipv4_192_168_network(self):
        assert _is_allowed("192.168.1.100", self.LOCAL_WHITELIST) is True

    def test_ipv6_loopback(self):
        assert _is_allowed("::1", self.LOCAL_WHITELIST) is True

    def test_ipv6_link_local(self):
        assert _is_allowed("fe80::1", self.LOCAL_WHITELIST) is True

    def test_ipv6_ula(self):
        assert _is_allowed("fd00::1", self.LOCAL_WHITELIST) is True

    # --- denied IPs ---

    def test_public_ipv4_denied(self):
        assert _is_allowed("8.8.8.8", self.LOCAL_WHITELIST) is False

    def test_public_ipv6_denied(self):
        assert _is_allowed("2001:4860:4860::8888", self.LOCAL_WHITELIST) is False

    def test_172_outside_range(self):
        assert _is_allowed("172.32.0.0", self.LOCAL_WHITELIST) is False

    # --- empty whitelist ---

    def test_empty_whitelist_denies_all(self):
        assert _is_allowed("127.0.0.1", []) is False

    # --- invalid inputs ---

    def test_invalid_hostname(self):
        assert _is_allowed("localhost", self.LOCAL_WHITELIST) is False

    def test_empty_string(self):
        assert _is_allowed("", self.LOCAL_WHITELIST) is False

    def test_malformed_ipv4(self):
        assert _is_allowed("256.0.0.1", self.LOCAL_WHITELIST) is False

    # --- single IP whitelist ---

    def test_single_ip_whitelist(self):
        assert _is_allowed("203.0.113.5", ["203.0.113.5/32"]) is True
        assert _is_allowed("203.0.113.6", ["203.0.113.5/32"]) is False


# ---------------------------------------------------------------------------
# McpAccessMiddleware integration tests
# ---------------------------------------------------------------------------


def _make_mcp_settings(mcp_whitelist=None, mcp_tokens=None):
    """Create a mock settings.security object."""

    class MockSecurity:
        def __init__(self):
            self.mcp_whitelist = mcp_whitelist if mcp_whitelist is not None else []
            self.mcp_tokens = mcp_tokens if mcp_tokens is not None else []

    class MockSettings:
        def __init__(self):
            self.security = MockSecurity()

    return MockSettings()


def _make_app() -> Starlette:
    """Build a minimal Starlette app with McpAccessMiddleware applied."""

    async def homepage(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(McpAccessMiddleware)
    return app


def _patch_client_ip(app, ip):
    """Return a modified app that overrides the client IP in ASGI scope."""
    original_build = app.build_middleware_stack

    async def patched_app(scope, receive, send):
        if scope["type"] == "http":
            scope["client"] = (ip, 12345) if ip is not None else None
        await original_build()(scope, receive, send)

    app.build_middleware_stack = lambda: patched_app
    return app


class TestMcpAccessMiddleware:
    """Verify McpAccessMiddleware allows/denies requests by IP and token."""

    def setup_method(self):
        clear_network_cache()

    def test_allowed_ip_passes(self):
        mock_settings = _make_mcp_settings(mcp_whitelist=["127.0.0.0/8"])
        app = _patch_client_ip(_make_app(), "127.0.0.1")
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/")
        assert response.status_code == 200
        assert response.text == "ok"

    def test_denied_ip_blocked(self):
        mock_settings = _make_mcp_settings(mcp_whitelist=["127.0.0.0/8"])
        app = _patch_client_ip(_make_app(), "8.8.8.8")
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/")
        assert response.status_code == 403
        assert "MCP access denied" in response.text

    def test_empty_whitelist_denies_all(self):
        mock_settings = _make_mcp_settings(mcp_whitelist=[], mcp_tokens=[])
        app = _patch_client_ip(_make_app(), "127.0.0.1")
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/")
        assert response.status_code == 403

    def test_missing_client_blocked(self):
        mock_settings = _make_mcp_settings(mcp_whitelist=["127.0.0.0/8"])
        app = _patch_client_ip(_make_app(), None)
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/")
        assert response.status_code == 403

    def test_bearer_token_bypasses_ip(self):
        mock_settings = _make_mcp_settings(
            mcp_whitelist=[], mcp_tokens=["secret-token-123"]
        )
        app = _patch_client_ip(_make_app(), "8.8.8.8")
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/", headers={"Authorization": "Bearer secret-token-123"}
            )
        assert response.status_code == 200

    def test_invalid_bearer_token_denied(self):
        mock_settings = _make_mcp_settings(
            mcp_whitelist=[], mcp_tokens=["secret-token-123"]
        )
        app = _patch_client_ip(_make_app(), "8.8.8.8")
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/", headers={"Authorization": "Bearer wrong-token"})
        assert response.status_code == 403

    def test_private_network_with_default_whitelist(self):
        default_whitelist = [
            "127.0.0.0/8",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "::1/128",
            "fe80::/10",
            "fc00::/7",
        ]
        mock_settings = _make_mcp_settings(mcp_whitelist=default_whitelist)
        app = _patch_client_ip(_make_app(), "192.168.1.100")
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/")
        assert response.status_code == 200

    def test_blocked_response_is_json(self):
        import json

        mock_settings = _make_mcp_settings(mcp_whitelist=["127.0.0.0/8"])
        app = _patch_client_ip(_make_app(), "1.2.3.4")
        with patch("module.mcp.security.settings", mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/")
        assert response.status_code == 403
        body = json.loads(response.text)
        assert "error" in body
