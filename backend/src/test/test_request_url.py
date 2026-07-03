"""Tests for network request_url: shared client configuration and reset."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.network.request_url import (
    RequestURL,
    get_shared_client,
    reset_shared_client,
)


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
        pool = client._transport._pool  # type: ignore[attr-defined]
        assert pool._keepalive_expiry is not None
        assert pool._keepalive_expiry > 0

    async def test_client_has_max_connections(self):
        """Shared client should have a connection pool limit."""
        client = await get_shared_client()
        pool = client._transport._pool  # type: ignore[attr-defined]
        assert pool._max_connections is not None
        assert pool._max_connections > 0

    async def test_client_follows_redirects(self):
        """Regression for #983: mikanime mirror returns 302 to the canonical
        URL but httpx refuses to follow by default, so the RSS fetch fails."""
        client = await get_shared_client()
        assert client.follow_redirects is True


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
    async def test_get_url_retries_without_resetting_client(self):
        """get_url should retry a ConnectTimeout on the same shared client,
        without closing/resetting it -- other concurrent callers may still
        have in-flight requests on that connection pool."""
        import httpx

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

        mock_reset.assert_not_called()
        assert call_count == 2
        assert result is not None
        assert result.status_code == 200


class TestReentrantContextManager:
    """Regression for the notification-dispatch concurrency restore.

    NotificationProvider holds one long-lived RequestContent instance
    (self._http) reused across ticks. core/loops.py now gathers notification
    sends concurrently (see rename_tick/rss_tick/offset_scan_tick), which
    means several overlapping ``async with provider:`` blocks -- and
    therefore several overlapping ``async with self._http:`` blocks -- can be
    in flight on the *same* RequestContent instance at once. __aexit__ must
    not null out self._client, or the first block to finish would break every
    other block still mid-request on that instance.
    """

    async def test_overlapping_blocks_on_same_instance_dont_race(self):
        req = RequestURL()
        seen_none = False

        async def use_it(delay: float) -> None:
            nonlocal seen_none
            async with req:
                if req._client is None:
                    seen_none = True
                await asyncio.sleep(delay)
                if req._client is None:
                    seen_none = True

        # The faster block exits while the slower one is still mid-"request";
        # before the fix this would null self._client out from under it.
        await asyncio.gather(use_it(0.0), use_it(0.05))

        assert not seen_none
        # Client stays valid after both blocks exit -- __aexit__ is a no-op.
        assert req._client is not None
