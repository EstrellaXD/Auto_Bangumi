"""Tests for network request_url: shared client configuration and reset."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from module.network.request_url import get_shared_client, reset_shared_client


@pytest.fixture(autouse=True)
async def _clean_shared_client():
    """Ensure shared client is reset after each test."""
    yield
    import module.network.request_url as mod

    if mod._shared_client is not None:
        await mod._shared_client.aclose()
        mod._shared_client = None
        mod._shared_client_proxy_key = None


class TestSharedClientLimits:
    async def test_client_has_keepalive_expiry(self):
        """Shared client should use a finite keepalive_expiry."""
        client = await get_shared_client()
        pool = client._transport._pool
        assert pool._keepalive_expiry is not None
        assert pool._keepalive_expiry > 0

    async def test_client_has_max_connections(self):
        """Shared client should have a connection pool limit."""
        client = await get_shared_client()
        pool = client._transport._pool
        assert pool._max_connections is not None
        assert pool._max_connections > 0


class TestResetSharedClient:
    async def test_reset_closes_existing_client(self):
        """reset_shared_client should close and clear the shared client."""
        client = await get_shared_client()
        assert client is not None

        await reset_shared_client()

        import module.network.request_url as mod

        assert mod._shared_client is None
        assert mod._shared_client_proxy_key is None

    async def test_reset_idempotent_when_no_client(self):
        """reset_shared_client should be safe when no client exists."""
        import module.network.request_url as mod

        mod._shared_client = None
        mod._shared_client_proxy_key = None
        await reset_shared_client()

    async def test_new_client_after_reset(self):
        """After reset, get_shared_client returns a fresh client."""
        old_client = await get_shared_client()
        await reset_shared_client()
        new_client = await get_shared_client()
        assert new_client is not old_client


class TestRetryWithReset:
    async def test_get_url_resets_on_connect_error(self):
        """get_url should call reset_shared_client after ConnectTimeout."""
        import httpx
        from module.network.request_url import RequestURL

        call_count = 0

        async def mock_get(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectTimeout("Connection timed out")
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            return resp

        with (
            patch("module.network.request_url.get_shared_client") as mock_get_client,
            patch(
                "module.network.request_url.reset_shared_client",
                new_callable=AsyncMock,
            ) as mock_reset,
        ):
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_get_client.return_value = mock_client

            async with RequestURL() as req:
                result = await req.get_url("https://example.com/test", retry=2)

        mock_reset.assert_called()
        assert call_count == 2
