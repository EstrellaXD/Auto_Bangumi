# RSS 请求 ConnectTimeout 修复设计

## 问题描述

RSS 订阅查询时频繁报 ConnectTimeout 错误，尤其在上一轮下载完成后、下一轮 RSS 循环时必现。

根因：httpx 共享客户端的连接池中，空闲连接在 RSS 循环间隔（900s）内过期失效，
但 `keepalive_expiry` 默认为 None（永不过期），httpx 仍尝试复用已死的连接。

## 修复方案

方案 B：keepalive_expiry 配置 + 重试时重建客户端 + 并发限制。

### 改动 1：连接池配置（request_url.py）

创建 AsyncClient 时传入 `httpx.Limits`，设置 `keepalive_expiry=60.0`，
使空闲超过 60 秒的连接自动从池中移除。

新增 `reset_shared_client()` 函数，用于在连接错误时强制销毁旧客户端。

在 `get_url()` 的重试逻辑中，遇到 `httpx.RequestError` 时调用 `reset_shared_client()`，
确保重试使用全新的连接。

### 改动 2：并发限制（engine.py）

在 `refresh_rss()` 中使用 `asyncio.Semaphore(5)` 限制并发 RSS 请求数量，
防止同时发起过多请求触发网站限流。

## 不改动的部分

- 共享客户端架构（设计合理，只缺过期管理）
- request_contents.py（问题不在解析层）
- sub_thread.py（循环逻辑无问题）
- 超时时间和重试次数（当前值合理）

## 相关 Issues

- #1008（ConnectTimeout，3.2.6 版本，完全一致）
- #1010（并发抓取被网站拦截）
- #742（长期网络连接问题）
- #701（运行一段时间后不工作）

## 测试

- 验证 `reset_shared_client()` 正确关闭旧客户端
- 验证 Semaphore 并发限制生效
- 模拟连接超时场景，验证重试恢复
