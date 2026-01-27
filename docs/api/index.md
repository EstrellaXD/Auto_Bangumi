# REST API 参考

AutoBangumi 在 `/api/v1` 路径下提供 REST API。除登录和设置向导外，所有端点都需要 JWT 认证。

**基础 URL：** `http://your-host:7892/api/v1`

**认证：** 将 JWT 令牌作为 cookie 或 `Authorization: Bearer <token>` 请求头传入。

**交互式文档：** 在开发模式下运行时，可在 `http://your-host:7892/docs` 访问 Swagger UI。

---

## 认证

### 登录

```
POST /auth/login
```

使用用户名和密码进行认证。

**请求体：**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应：** 设置包含 JWT 令牌的认证 cookie。

### 刷新令牌

```
GET /auth/refresh_token
```

刷新当前的认证令牌。

### 登出

```
GET /auth/logout
```

清除认证 cookie 并登出。

### 更新凭据

```
POST /auth/update
```

更新用户名和/或密码。

**请求体：**
```json
{
  "username": "string",
  "password": "string"
}
```

---

## Passkey / WebAuthn <Badge type="tip" text="v3.2+" />

使用 WebAuthn/FIDO2 Passkey 进行无密码认证。

### 注册 Passkey

```
POST /passkey/register/options
```

获取 WebAuthn 注册选项（质询、依赖方信息）。

```
POST /passkey/register/verify
```

验证并保存来自浏览器的 Passkey 注册响应。

### 使用 Passkey 认证

```
POST /passkey/auth/options
```

获取 WebAuthn 认证质询选项。

```
POST /passkey/auth/verify
```

验证 Passkey 认证响应并签发 JWT 令牌。

### 管理 Passkey

```
GET /passkey/list
```

列出当前用户所有已注册的 Passkey。

```
POST /passkey/delete
```

通过凭据 ID 删除已注册的 Passkey。

---

## 配置

### 获取配置

```
GET /config/get
```

获取当前应用程序配置。

**响应：** 完整配置对象，包括 `program`、`downloader`、`rss_parser`、`bangumi_manager`、`notification`、`proxy` 和 `experimental_openai` 部分。

### 更新配置

```
PATCH /config/update
```

部分更新应用程序配置。只需包含您想要更改的字段。

**请求体：** 部分配置对象。

---

## 番剧（动画规则）

### 列出所有番剧

```
GET /bangumi/get/all
```

获取所有动画下载规则。

### 通过 ID 获取番剧

```
GET /bangumi/get/{bangumi_id}
```

通过 ID 获取特定动画规则。

### 更新番剧

```
PATCH /bangumi/update/{bangumi_id}
```

更新动画规则的元数据（标题、季度、集数偏移等）。

### 删除番剧

```
DELETE /bangumi/delete/{bangumi_id}
```

删除单个动画规则及其关联的种子。

```
DELETE /bangumi/delete/many/
```

批量删除多个动画规则。

**请求体：**
```json
{
  "bangumi_ids": [1, 2, 3]
}
```

### 禁用/启用番剧

```
DELETE /bangumi/disable/{bangumi_id}
```

禁用动画规则（保留文件，停止下载）。

```
DELETE /bangumi/disable/many/
```

批量禁用多个动画规则。

```
GET /bangumi/enable/{bangumi_id}
```

重新启用之前禁用的动画规则。

### 刷新海报

```
GET /bangumi/refresh/poster/all
```

从 TMDB 刷新所有动画的海报图片。

```
GET /bangumi/refresh/poster/{bangumi_id}
```

刷新特定动画的海报图片。

### 日历

```
GET /bangumi/refresh/calendar
```

从 Bangumi.tv 刷新动画放送日历数据。

### 重置全部

```
GET /bangumi/reset/all
```

删除所有动画规则。请谨慎使用。

---

## RSS 订阅源

### 列出所有订阅源

```
GET /rss
```

获取所有已配置的 RSS 订阅源。

### 添加订阅源

```
POST /rss/add
```

添加新的 RSS 订阅源。

**请求体：**
```json
{
  "url": "string",
  "aggregate": true,
  "parser": "mikan"
}
```

### 启用/禁用订阅源

```
POST /rss/enable/many
```

启用多个 RSS 订阅源。

```
PATCH /rss/disable/{rss_id}
```

禁用单个 RSS 订阅源。

```
POST /rss/disable/many
```

批量禁用多个 RSS 订阅源。

### 删除订阅源

```
DELETE /rss/delete/{rss_id}
```

删除单个 RSS 订阅源。

```
POST /rss/delete/many
```

批量删除多个 RSS 订阅源。

### 更新订阅源

```
PATCH /rss/update/{rss_id}
```

更新 RSS 订阅源的配置。

### 刷新订阅源

```
GET /rss/refresh/all
```

手动触发刷新所有 RSS 订阅源。

```
GET /rss/refresh/{rss_id}
```

刷新特定的 RSS 订阅源。

### 获取订阅源中的种子

```
GET /rss/torrent/{rss_id}
```

获取从特定 RSS 订阅源解析的种子列表。

### 分析与订阅

```
POST /rss/analysis
```

分析 RSS URL 并提取动画元数据，但不订阅。

**请求体：**
```json
{
  "url": "string"
}
```

```
POST /rss/collect
```

从 RSS 订阅源下载所有剧集（用于已完结动画）。

```
POST /rss/subscribe
```

订阅 RSS 订阅源以自动下载连载中的动画。

---

## 搜索

### 搜索番剧（Server-Sent Events）

```
GET /search/bangumi?keyword={keyword}&provider={provider}
```

搜索动画种子。以 Server-Sent Events (SSE) 流的形式返回结果，提供实时更新。

**查询参数：**
- `keyword` — 搜索关键词
- `provider` — 搜索提供者（例如 `mikan`、`nyaa`、`dmhy`）

**响应：** 包含解析后搜索结果的 SSE 流。

### 列出搜索提供者

```
GET /search/provider
```

获取可用搜索提供者的列表。

---

## 程序控制

### 获取状态

```
GET /status
```

获取程序状态，包括版本、运行状态和 first_run 标志。

**响应：**
```json
{
  "status": "running",
  "version": "3.2.0",
  "first_run": false
}
```

### 启动程序

```
GET /start
```

启动主程序（RSS 检查、下载、重命名）。

### 重启程序

```
GET /restart
```

重启主程序。

### 停止程序

```
GET /stop
```

停止主程序（WebUI 仍可访问）。

### 关闭

```
GET /shutdown
```

关闭整个应用程序（重启 Docker 容器）。

### 检查下载器

```
GET /check/downloader
```

测试与已配置的下载器（qBittorrent）的连接。

---

## 下载器管理 <Badge type="tip" text="v3.2+" />

直接从 AutoBangumi 管理下载器中的种子。

### 列出种子

```
GET /downloader/torrents
```

获取 Bangumi 分类中的所有种子。

### 暂停种子

```
POST /downloader/torrents/pause
```

通过哈希暂停种子。

**请求体：**
```json
{
  "hashes": ["hash1", "hash2"]
}
```

### 恢复种子

```
POST /downloader/torrents/resume
```

通过哈希恢复已暂停的种子。

**请求体：**
```json
{
  "hashes": ["hash1", "hash2"]
}
```

### 删除种子

```
POST /downloader/torrents/delete
```

删除种子，可选择是否删除文件。

**请求体：**
```json
{
  "hashes": ["hash1", "hash2"],
  "delete_files": false
}
```

---

## 设置向导 <Badge type="tip" text="v3.2+" />

这些端点仅在首次运行设置期间可用（设置完成前）。它们**不**需要认证。设置完成后，所有端点返回 `403 Forbidden`。

### 检查设置状态

```
GET /setup/status
```

检查是否需要设置向导（首次运行）。

**响应：**
```json
{
  "need_setup": true
}
```

### 测试下载器连接

```
POST /setup/test-downloader
```

使用提供的凭据测试与下载器的连接。

**请求体：**
```json
{
  "type": "qbittorrent",
  "host": "172.17.0.1:8080",
  "username": "admin",
  "password": "adminadmin",
  "ssl": false
}
```

### 测试 RSS 订阅源

```
POST /setup/test-rss
```

验证 RSS 订阅源 URL 是否可访问和可解析。

**请求体：**
```json
{
  "url": "https://mikanime.tv/RSS/MyBangumi?token=xxx"
}
```

### 测试通知

```
POST /setup/test-notification
```

使用提供的设置发送测试通知。

**请求体：**
```json
{
  "type": "telegram",
  "token": "bot_token",
  "chat_id": "chat_id"
}
```

### 完成设置

```
POST /setup/complete
```

保存所有配置并将设置标记为完成。创建标记文件 `config/.setup_complete`。

**请求体：** 完整配置对象。

---

## 日志

### 获取日志

```
GET /log
```

获取完整的应用程序日志文件。

### 清除日志

```
GET /log/clear
```

清除日志文件。

---

## 响应格式

所有 API 响应遵循统一格式：

```json
{
  "msg_en": "Success message in English",
  "msg_zh": "成功消息（中文）",
  "status": true
}
```

错误响应包含适当的 HTTP 状态码（400、401、403、404、500）以及中英文错误消息。
