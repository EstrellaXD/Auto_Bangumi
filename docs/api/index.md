# REST API 参考

AutoBangumi 在 `/api/v1` 下提供 REST API。WebUI 使用的也是这套接口。

**基础 URL：** `http://your-host:7892/api/v1`

**交互式文档：** 本页只列出端点和用途。请求与响应的字段以运行中实例的 `http://your-host:7892/docs`（Swagger UI，由 FastAPI 根据代码生成）为准。插件路由不出现在 `/docs` 中。

## 认证

AB 接受两种凭据：

- **浏览器会话**：`POST /auth/login` 以表单字段 `username`、`password` 登录，成功后 AB 设置 HttpOnly Cookie `token`。WebUI 使用这种方式。
- **API 令牌**：在 设置 → 用户与访问控制 → API 令牌 中创建 `scope=api` 的令牌（或调用 `POST /tokens`），明文只显示一次。请求时带上 `Authorization: Bearer <令牌>`。

```bash
curl -H "Authorization: Bearer $AB_TOKEN" http://your-host:7892/api/v1/status
```

- 请求带 `Authorization` 头时，AB 只校验该令牌，不再看 Cookie。
- 未认证或凭据无效返回 `401`。
- 账户管理端点（`/auth/update`、`/users`、`/tokens`、Passkey 的注册与管理）只接受浏览器会话，用 API 令牌访问返回 `403`。
- 以下端点不需要认证：`/auth/login`、`/passkey/auth/*`、设置向导 `/setup/*`（`GET /setup/status` 始终可用，其它端点在设置完成后返回 `403`）和根路径的 `/health`。
- `/auth/refresh_token` 与 `/auth/logout` 不看 `Authorization` 头，只使用会话 Cookie。`refresh_token` 没有有效 Cookie 时返回 `401`。登录与 Passkey 登录受 `security.login_whitelist` 限制。
- 本地开发时，设置环境变量 `AB_DEV_NO_AUTH=1` 可跳过全部认证。不要在生产环境中设置它。

## 认证与账户

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/auth/login` | 用户名和密码登录，设置会话 Cookie |
| `POST` | `/auth/refresh_token` | 延长当前会话 |
| `POST` | `/auth/logout` | 注销当前会话并清除 Cookie |
| `GET` | `/auth/me` | 当前用户 |
| `POST` | `/auth/update` | 修改当前账户，并轮换它的全部会话 |
| `GET` / `POST` | `/users` | 列出 / 创建用户 |
| `PATCH` / `DELETE` | `/users/{user_id}` | 修改 / 删除用户 |
| `GET` / `POST` | `/tokens` | 列出 / 创建 API 令牌（`scope` 为 `api` 或 `mcp`，可设 `expires_at`） |
| `DELETE` | `/tokens/{token_id}` | 吊销令牌 |
| `POST` | `/passkey/register/options`、`/passkey/register/verify` | 注册 Passkey |
| `POST` | `/passkey/auth/options`、`/passkey/auth/verify` | 用 Passkey 登录 |
| `GET` | `/passkey/list` | 列出当前用户的 Passkey |
| `POST` | `/passkey/delete` | 删除 Passkey |

## 程序

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/status` | 版本、运行状态、是否首次运行 |
| `POST` | `/start`、`/stop`、`/restart` | 启动 / 停止 / 重启后台任务 |
| `POST` | `/shutdown` | 关闭程序 |
| `GET` | `/check/downloader` | 检查默认下载器是否可用 |
| `GET` | `/log` | 读取日志 |
| `POST` | `/log/clear` | 清空日志 |
| `GET` | `/update/check` | 查询最新版本与在线更新状态 |
| `POST` | `/update/apply` | 下载并应用最新更新，成功后重启 |
| `POST` | `/update/rollback` | 回滚到上一个更新版本，没有备份时回到镜像自带版本 |
| `GET` | `/health`（根路径，不在 `/api/v1` 下） | 存活探针，总是返回 `200`：`{"status", "version", "db_ok"}` |

## 配置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/config/get` | 当前配置，秘密字段已掩码 |
| `PATCH` | `/config/update` | 保存并重新加载配置；收到掩码的秘密字段保留原值 |
| `POST` | `/config/llm/models` | 列出所选 LLM 提供商的可用模型 |
| `GET` | `/config/llm/providers` | LLM 提供商列表 |
| `POST` | `/config/llm/providers/{provider_id}/install` | 安装 LLM 提供商插件 |
| `DELETE` | `/config/llm/providers/{provider_id}` | 卸载 LLM 提供商插件 |
| `POST` | `/config/llm/providers/{provider_id}/auth/begin`、`/auth/complete` | 订阅类提供商的授权流程 |
| `GET` | `/config/llm/providers/{provider_id}/auth/status` | 授权状态 |
| `DELETE` | `/config/llm/providers/{provider_id}/auth` | 断开授权 |

## 番剧

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/bangumi/get/all` | 全部番剧规则 |
| `GET` | `/bangumi/get/{bangumi_id}` | 单个规则 |
| `PATCH` | `/bangumi/update/{bangumi_id}` | 修改规则 |
| `DELETE` | `/bangumi/delete/{bangumi_id}` | 删除规则 |
| `POST` | `/bangumi/delete/many` | 批量删除 |
| `POST` | `/bangumi/disable/{bangumi_id}`、`/bangumi/enable/{bangumi_id}` | 停用 / 启用规则 |
| `POST` | `/bangumi/disable/many` | 批量停用 |
| `PATCH` | `/bangumi/archive/{bangumi_id}`、`/bangumi/unarchive/{bangumi_id}` | 归档 / 取消归档 |
| `PATCH` | `/bangumi/{bangumi_id}/weekday` | 手动设置放送星期 |
| `GET` | `/bangumi/refresh/poster/all`、`/bangumi/refresh/poster/{bangumi_id}` | 刷新海报 |
| `GET` | `/bangumi/refresh/calendar` | 刷新放送日历 |
| `GET` | `/bangumi/refresh/metadata` | 刷新 TMDB 元数据，并自动归档已完结的番剧 |
| `POST` | `/bangumi/reset/all` | 删除全部规则 |
| `GET` | `/bangumi/needs-review` | 需要确认集数偏移的番剧 |
| `GET` | `/bangumi/suggest-offset/{bangumi_id}` | 根据 TMDB 集数建议偏移 |
| `POST` | `/bangumi/detect-offset` | 检测季度 / 集数与 TMDB 不一致 |
| `POST` | `/bangumi/apply-offset/{bangumi_id}`、`/bangumi/apply-offset/many` | 应用建议的偏移并触发一次重命名 |
| `POST` | `/bangumi/dismiss-review/{bangumi_id}` | 清除「待确认」标记 |
| `GET` / `DELETE` | `/bangumi/{bangumi_id}/torrents` | 列出 / 删除该番剧的种子记录 |
| `DELETE` | `/bangumi/{bangumi_id}/torrents/{torrent_id}` | 删除一条种子记录 |
| `GET` / `DELETE` | `/bangumi/torrents/orphans` | 列出 / 删除不属于任何番剧的种子记录 |
| `GET` | `/bangumi/torrents/orphans/count` | 孤立种子记录的数量 |
| `DELETE` | `/bangumi/torrents/orphans/{torrent_id}` | 删除一条孤立种子记录 |

## 电影

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/movie/get/all`、`/movie/get/{movie_id}` | 全部 / 单个电影规则 |
| `PATCH` | `/movie/update/{movie_id}` | 修改 |
| `DELETE` | `/movie/delete/{movie_id}` | 删除 |
| `DELETE` | `/movie/disable/{movie_id}` | 停用 |
| `GET` | `/movie/enable/{movie_id}` | 启用 |

## RSS 订阅

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/rss` | 全部订阅 |
| `POST` | `/rss/add` | 添加订阅 |
| `PATCH` | `/rss/update/{rss_id}` | 修改订阅 |
| `DELETE` | `/rss/delete/{rss_id}` | 删除订阅 |
| `POST` | `/rss/delete/many` | 批量删除 |
| `PATCH` | `/rss/disable/{rss_id}` | 停用 |
| `POST` | `/rss/disable/many`、`/rss/enable/many` | 批量停用 / 启用 |
| `POST` | `/rss/refresh/all`、`/rss/refresh/{rss_id}` | 立即刷新 |
| `GET` | `/rss/torrent/{rss_id}` | 该订阅的种子 |
| `POST` | `/rss/analysis` | 解析一个 RSS 链接，返回识别出的番剧 |
| `POST` | `/rss/collect` | 下载整季（收集） |
| `POST` | `/rss/subscribe` | 订阅 |

## 搜索

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/search/bangumi?site=<站点>&keywords=<关键词>` | Server-Sent Events，逐条推送搜索结果；多个关键词以空格分隔 |
| `GET` | `/search/provider` | 可用的搜索站点（含插件提供的站点） |
| `GET` / `PUT` | `/search/provider/config` | 读取 / 保存用户配置的搜索站点 |

## 下载器

AB 4.0 可以配置多个下载器实例（`plugins.instances`）。种子列表合并所有实例，每条带 `downloader_id`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/downloader/instances` | 下载器实例：`{"default": <默认实例 id>, "instances": [{"id", "provider"}]}` |
| `GET` | `/downloader/torrents` | 所有实例的种子；不可用的实例跳过 |
| `POST` | `/downloader/torrents/pause`、`/resume`、`/delete` | 暂停 / 恢复 / 删除种子 |
| `POST` | `/downloader/torrents/tag` | 给种子打番剧 id 标签 |
| `POST` | `/downloader/torrents/tag/auto` | 按名称与路径为未打标签的种子自动打标签 |
| `GET` | `/downloader/rename-conflicts` | 等待用户处理的重命名冲突 |
| `POST` | `/downloader/rename-conflicts/{operation_id}/retry` | 清除一条冲突，下一轮重命名时重新检查 |

## 通知中心

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` / `DELETE` | `/notification/messages` | 列出 / 清空站内通知 |
| `GET` | `/notification/messages/unread-count` | 未读数量 |
| `POST` | `/notification/messages/read-all` | 全部标为已读 |
| `POST` | `/notification/messages/{message_id}/read` | 标为已读 |
| `DELETE` | `/notification/messages/{message_id}` | 删除一条 |
| `POST` | `/notification/test` | 按序号测试已保存的通知渠道 |
| `POST` | `/notification/test-config` | 测试未保存的通知渠道配置 |

## 事件流

`GET /events/stream` 是一条 Server-Sent Events 连接，WebUI 用它代替轮询。

| `event` | 何时推送 | `data` |
| --- | --- | --- |
| `status` | 每 3 秒 | 与 `GET /status` 相同的结构 |
| `downloader` | 每 5 秒 | 所有实例的种子；下载器不可用时为 `null` |
| `log` | 每 10 秒 | 日志尾部 |
| `update` | 在线更新进行中且进度变化时 | 更新进度 |
| `notification` | 连接建立时，以及通知中心变化时 | 通知中心状态，含未读数 `unread_count` |
| `bus` | 事件总线上有事件时 | `{"kind": <事件名>, "payload": {...}}`，包括宿主事件和插件事件 |

```bash
curl -N -H "Authorization: Bearer $AB_TOKEN" http://your-host:7892/api/v1/events/stream
```

`bus` 帧中的事件名与字段见 [插件开发 → 事件](/dev/plugins/events)。前端插件组件用 `host.events.on(kind, callback)` 订阅同样的帧。

## 插件

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/plugins` | 已发现的插件、状态、配置表单 schema 与当前配置（已掩码） |
| `PUT` | `/plugins/settings` | 修改 `allow_unsigned`（允许未签名插件） |
| `PUT` | `/plugins/{plugin_id}` | 启用 / 停用插件或修改配置，保存后立即生效；配置不合法返回 `422` |
| `GET` | `/plugins/providers` | 插件提供的 Provider id，按扩展点分组 |
| `GET` | `/plugins/ui` | 已启用插件声明的前端挂载点 |
| `GET` | `/plugins/catalog` | 签名目录中可安装的插件；目录不可达返回 `502` |
| `POST` | `/plugins/{plugin_id}/install` | 从签名目录安装或升级插件，并启用 |
| `DELETE` | `/plugins/{plugin_id}` | 卸载经签名目录安装的插件 |
| `GET` | `/plugins/{plugin_id}/web/{path}` | 插件 `web/` 目录下的前端静态文件 |
| 任意 | `/plugins/{plugin_id}/{path}` | 插件自己的路由，见 [REST 路由](/dev/plugins/points/api-router) |

## 设置向导

这些端点不需要认证。`GET /setup/status` 始终可用，返回 `need_setup`（设置完成后为 `false`）。其它端点只在首次设置完成前可用，完成后返回 `403`。`/setup/complete` 还要求浏览器会话，或 `admin` 账户仍为出厂密码 `adminadmin`；否则返回 `403`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/setup/status` | 是否需要设置向导 |
| `POST` | `/setup/test-downloader` | 测试下载器连接 |
| `POST` | `/setup/test-rss` | 测试 RSS 链接 |
| `POST` | `/setup/test-notification` | 发送测试通知 |
| `POST` | `/setup/complete` | 保存向导中的全部配置，并标记设置完成 |

## MCP

AB 在根路径的 `/mcp` 下提供 MCP 服务：Streamable HTTP 传输的端点为 `/mcp`；旧版 SSE 传输仍可用，客户端连接 `GET /mcp/sse`，并向 `POST /mcp/messages/` 发送消息。

- 访问控制与 REST API 分开：客户端 IP 在 `security.mcp_whitelist` 内，或请求带 `scope=mcp` 的令牌（`Authorization: Bearer <令牌>`）。`mcp_whitelist` 为空时拒绝所有基于 IP 的访问，令牌仍然有效。
- 内置工具：`list_anime`、`get_anime`、`search_anime`、`subscribe_anime`、`unsubscribe_anime`、`list_downloads`、`list_rss_feeds`、`get_program_status`、`refresh_feeds`、`update_anime`。
- 内置资源：`autobangumi://anime/list`、`autobangumi://anime/{id}`、`autobangumi://status`、`autobangumi://rss/feeds`。
- 已启用插件提供的工具名为 `<插件 id>__<id>`，资源 URI 为 `autobangumi://plugins/<插件 id>/<id>`，见 [MCP 工具与资源](/dev/plugins/points/mcp)。

## 响应与错误

- 许多操作类端点返回 `{"status": true, "msg_en": "...", "msg_zh": "..."}`。查询类端点直接返回数据。具体结构见 `/docs`。
- 错误使用标准 HTTP 状态码：`401` 未认证，`403` 无权限，`404` 不存在，`422` 参数校验失败，`500` 服务器错误。
