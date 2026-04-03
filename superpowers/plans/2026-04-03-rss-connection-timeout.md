# RSS ConnectTimeout 修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 RSS 请求因 httpx 连接池过期连接导致的 ConnectTimeout 错误。

**Architecture:** 在现有共享客户端架构上增加两层防护：(1) 连接池 keepalive 过期配置 + 重试时重建客户端，(2) RSS 并发请求信号量限制。两个改动互相独立，分别位于 `request_url.py` 和 `engine.py`。

**Tech Stack:** Python 3.10+, httpx 0.28.1, httpcore 1.0.9, asyncio, pytest + pytest-asyncio

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/src/module/network/request_url.py` | Modify | 添加连接池 Limits 配置；新增 `reset_shared_client()`；重试时调用重建 |
| `backend/src/module/rss/engine.py` | Modify | `refresh_rss()` 中添加 Semaphore 并发限制 |
| `backend/src/test/test_request_url.py` | Create | 测试连接池配置、客户端重建、重试时重建逻辑 |
| `backend/src/test/test_rss_engine_new.py` | Modify | 添加并发限制相关测试 |

---

## Task 1: 连接池 Limits 配置

**Files:**
- Modify: `backend/src/module/network/request_url.py:22-49`
- Test: `backend/src/test/test_request_url.py`

- [ ] **Step 1: 写失败测试 — 验证共享客户端使用 Limits 配置**

Create `backend/src/test/test_request_url.py`:

```python
"""Tests for network request_url: shared client configuration and reset."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from module.network.request_url import get_shared_client, reset_shared_client, _proxy_config_key


@pytest.fixture(autouse=True)
def _clean_shared_client():
    """Ensure shared client is reset after each test."""
    yield
    import module.network.request_url as mod
    if mod._shared_client is not None:
        import asyncio
        asyncio.get_event_loop().run_until_complete(mod._shared_client.aclose())
        mod._shared_client = None
        mod._shared_client_proxy_key = None


class TestSharedClientLimits:
    async def test_client_has_keepalive_expiry(self):
        """Shared client should use a finite keepalive_expiry."""
        client = await get_shared_client()
        # httpx stores limits internally; check via _transport
        pool = client._transport._pool
        assert pool._keepalive_expiry is not None
        assert pool._keepalive_expiry > 0

    async def test_client_has_max_connections(self):
        """Shared client should have a connection pool limit."""
        client = await get_shared_client()
        pool = client._transport._pool
        assert pool._max_connections is not None
        assert pool._max_connections > 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest src/test/test_request_url.py::TestSharedClientLimits -v`
Expected: FAIL — `_keepalive_expiry` 可能是 None（取决于当前默认值）

- [ ] **Step 3: 在 request_url.py 添加 Limits 配置**

Modify `backend/src/module/network/request_url.py`:

在 `get_shared_client()` 函数中，将所有 `_shared_client = httpx.AsyncClient(...)` 调用添加 `limits` 参数：

```python
# 在文件顶部，import 区域后添加
# RSS 循环间隔 900s，远超服务端 keep-alive 超时（60-120s）
# keepalive_expiry=60 让空闲连接在过期前主动丢弃
# max_connections=20 足够覆盖典型订阅数量
_CONNECTION_LIMITS = httpx.Limits(
    max_keepalive_connections=5,
    max_connections=20,
    keepalive_expiry=60.0,
)
```

然后修改 `get_shared_client()` 中的每个 `httpx.AsyncClient(...)` 调用（约第 36, 43, 45, 47 行），添加 `limits=_CONNECTION_LIMITS` 参数：

```python
# 第 36 行
_shared_client = httpx.AsyncClient(proxy=proxy_url, timeout=timeout, limits=_CONNECTION_LIMITS)
# 第 43 行
_shared_client = httpx.AsyncClient(transport=transport, timeout=timeout, limits=_CONNECTION_LIMITS)
# 第 45 行
_shared_client = httpx.AsyncClient(timeout=timeout, limits=_CONNECTION_LIMITS)
# 第 47 行
_shared_client = httpx.AsyncClient(timeout=timeout, limits=_CONNECTION_LIMITS)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest src/test/test_request_url.py::TestSharedClientLimits -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/src/module/network/request_url.py backend/src/test/test_request_url.py
git commit -m "feat(network): add connection pool limits with keepalive expiry"
```

---

## Task 2: 客户端重建函数 + 重试时调用

**Files:**
- Modify: `backend/src/module/network/request_url.py:12-49, 75-99`
- Test: `backend/src/test/test_request_url.py`

- [ ] **Step 1: 写失败测试 — 验证 reset_shared_client 销毁旧客户端**

Append to `backend/src/test/test_request_url.py`:

```python
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
        # Should not raise
        await reset_shared_client()

    async def test_new_client_after_reset(self):
        """After reset, get_shared_client returns a fresh client."""
        old_client = await get_shared_client()
        await reset_shared_client()
        new_client = await get_shared_client()
        assert new_client is not old_client
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest src/test/test_request_url.py::TestResetSharedClient -v`
Expected: FAIL — `reset_shared_client` 不存在

- [ ] **Step 3: 在 request_url.py 添加 reset_shared_client 函数**

在 `get_shared_client()` 函数后面（约第 49 行之后），添加：

```python
async def reset_shared_client():
    """关闭并清除共享客户端，下次请求时自动创建新连接池。"""
    global _shared_client, _shared_client_proxy_key
    if _shared_client is not None:
        await _shared_client.aclose()
    _shared_client = None
    _shared_client_proxy_key = None
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest src/test/test_request_url.py::TestResetSharedClient -v`
Expected: PASS

- [ ] **Step 5: 写测试 — 验证 get_url 在连接错误时重建客户端**

Append to `backend/src/test/test_request_url.py`:

```python
class TestRetryWithReset:
    async def test_get_url_resets_client_on_connect_error(self):
        """get_url should reset shared client when encountering a connection error."""
        import httpx
        from module.network.request_url import RequestURL

        # Mock client that raises ConnectTimeout on first call, succeeds on second
        call_count = 0
        original_get = None

        async def mock_get(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectTimeout("Connection timed out")
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            return resp

        with patch("module.network.request_url.get_shared_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_get_client.return_value = mock_client

            async with RequestURL() as req:
                result = await req.get_url("https://example.com/test", retry=2)

        # reset_shared_client should have been called after the ConnectTimeout
        assert call_count >= 1
```

- [ ] **Step 6: 在 get_url 重试逻辑中调用 reset_shared_client**

Modify `backend/src/module/network/request_url.py` 的 `get_url` 方法中 `except httpx.RequestError` 分支：

```python
except httpx.RequestError as e:
    logger.warning(
        f"[Network] Request error for {url}: {type(e).__name__}. Retry {try_time + 1}/{retry}"
    )
    try_time += 1
    if try_time >= retry:
        break
    # 清除连接池中的过期连接
    await reset_shared_client()
    self._client = await get_shared_client()
    await asyncio.sleep(5)
```

- [ ] **Step 7: 在 post_url 方法中同样添加重试重建逻辑**

修改 `post_url` 方法的 `except httpx.RequestError` 分支，添加相同的重建逻辑：

```python
except httpx.RequestError:
    logger.warning(f"[Network] Cannot connect to {url}. Wait for 5 seconds.")
    try_time += 1
    if try_time >= retry:
        break
    await reset_shared_client()
    self._client = await get_shared_client()
    await asyncio.sleep(5)
```

- [ ] **Step 8: 运行测试验证通过**

Run: `cd backend && uv run pytest src/test/test_request_url.py -v`
Expected: ALL PASS

- [ ] **Step 9: 提交**

```bash
git add backend/src/module/network/request_url.py backend/src/test/test_request_url.py
git commit -m "feat(network): reset shared client on connection errors to clear stale connections"
```

---

## Task 3: RSS 请求并发限制

**Files:**
- Modify: `backend/src/module/rss/engine.py:145-173`
- Test: `backend/src/test/test_rss_engine_new.py`

- [ ] **Step 1: 写失败测试 — 验证并发限制生效**

Append to `backend/src/test/test_rss_engine_new.py`:

```python
import asyncio


class TestRefreshRssConcurrency:
    async def test_concurrent_requests_limited(self, rss_engine):
        """refresh_rss should limit concurrent requests via semaphore."""
        rss_items = [make_rss_item(name=f"Feed {i}", url=f"https://feed{i}.com/rss") for i in range(10)]
        for item in rss_items:
            rss_engine.rss.add(item)

        active_count = 0
        max_active = 0
        lock = asyncio.Lock()

        async def track_concurrency(rss_item):
            nonlocal active_count, max_active
            async with lock:
                active_count += 1
                max_active = max(max_active, active_count)
            await asyncio.sleep(0.01)
            async with lock:
                active_count -= 1
            return [], None

        with patch.object(rss_engine, "_pull_rss_with_status", side_effect=track_concurrency):
            client = AsyncMock()
            await rss_engine.refresh_rss(client)

        # Semaphore limit is 5, so max_active should not exceed 5
        assert max_active <= 5
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && uv run pytest src/test/test_rss_engine_new.py::TestRefreshRssConcurrency -v`
Expected: FAIL — 当前 `max_active` 会是 10（所有请求同时执行）

- [ ] **Step 3: 在 engine.py 添加 Semaphore 并发限制**

Modify `backend/src/module/rss/engine.py` 的 `refresh_rss` 方法，在 `asyncio.gather` 之前添加信号量：

```python
async def refresh_rss(self, client: DownloadClient, rss_id: Optional[int] = None):
    # Get All RSS Items
    if not rss_id:
        rss_items: list[RSSItem] = self.rss.search_active()
    else:
        rss_item = self.rss.search_id(rss_id)
        rss_items = [rss_item] if rss_item else []
    # From RSS Items, fetch all torrents with concurrency limit
    logger.debug("[Engine] Get %s RSS items", len(rss_items))
    # 限制并发请求数，防止被 RSS 源限流
    # 5 个并发足以覆盖典型场景，同时不会触发大多数站点限流
    semaphore = asyncio.Semaphore(5)

    async def _limited_pull(rss_item):
        async with semaphore:
            return await self._pull_rss_with_status(rss_item)

    results = await asyncio.gather(
        *[_limited_pull(item) for item in rss_items]
    )
    # ... 后续处理不变 ...
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && uv run pytest src/test/test_rss_engine_new.py::TestRefreshRssConcurrency -v`
Expected: PASS — `max_active <= 5`

- [ ] **Step 5: 运行现有 RSS engine 测试确保无回归**

Run: `cd backend && uv run pytest src/test/test_rss_engine_new.py -v`
Expected: ALL PASS

- [ ] **Step 6: 提交**

```bash
git add backend/src/module/rss/engine.py backend/src/test/test_rss_engine_new.py
git commit -m "feat(rss): limit concurrent RSS requests with semaphore to avoid rate limiting"
```

---

## Task 4: 全量测试 + lint

**Files:** None (verification only)

- [ ] **Step 1: 运行全量测试**

Run: `cd backend && uv run pytest src/test/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: 运行 lint**

Run: `cd backend && uv run ruff check src`
Expected: No errors

- [ ] **Step 3: 运行 formatter**

Run: `cd backend && uv run black src --check`
Expected: No changes needed
