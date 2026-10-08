# 插件开发

::: warning 预览版 SDK
插件 SDK `ab_sdk` 在 4.0 期间为 0.x 版本，接口可能有不兼容调整；4.1 起冻结 1.0，之后遵守语义化版本。清单里的 `sdk` 字段声明你依赖的版本范围，AB 会拒绝加载不兼容的插件。
:::

插件是一个 Python 包，可以给 AutoBangumi 增加：

| 扩展点 | 常量 | 返回值 | 用户如何启用 |
| --- | --- | --- | --- |
| 下载器 | `points.DOWNLOADER` | `DownloaderFactory` | 设置 → 下载器 → 类型 |
| 通知渠道 | `points.NOTIFIER` | `NotifierFactory` | 设置 → 通知 → 添加渠道 |
| LLM 解析提供商 | `points.LLM_PROVIDER` | `LLMProviderAdapter` 子类 | 设置 → LLM → 提供商 |
| 搜索站点 | `points.SEARCH_SITE` | `SearchSite` | 搜索框的站点列表 |
| 定时任务 | `points.SCHEDULED_TASK` | `ScheduledTask` | 插件启用即生效 |
| REST 路由 | `points.API_ROUTER` | `fastapi.APIRouter` | 插件启用即生效 |
| MCP 工具 | `points.MCP_TOOL` | `McpTool` | 插件启用即生效 |
| MCP 资源 | `points.MCP_RESOURCE` | `McpResource` | 插件启用即生效 |

此外，插件可以订阅系统事件（`@subscribe`）、改写通知文案（`@hook(points.MESSAGE_TEMPLATE)`），并使用私有的键值存储和数据目录。RSS 过滤、重命名等流水线扩展点会在后续版本陆续开放。

## 目录结构

```
config/plugins/local/my-plugin/     # 目录名必须与清单中的 id 相同
├── plugin.toml
├── my_plugin.py                    # 也可以是包，插件内部可以用相对导入
└── vendor/                         # 可选：纯 Python 依赖（禁止 .so/.pyd）
```

```toml
# plugin.toml
[plugin]
id = "my-plugin"              # 小写字母、数字、连字符
name = "我的插件"
version = "0.1.0"
sdk = ">=0.2,<1"              # 依赖的 ab_sdk 版本范围
entry = "my_plugin:MyPlugin"  # 模块:Plugin 子类，相对插件目录
description = "一句话说明"
permissions = ["network"]     # 仅用于向用户展示，不做强制
```

本地插件未经签名。要让 AB 加载它，需要在 **设置 → 插件** 中先打开「允许未签名插件」，再启用该插件。插件与 AB 在同一进程中运行，拥有完整权限。

## 第一个插件：Bark 风格的推送渠道

```python
from pydantic import BaseModel, Field

from ab_sdk import Plugin, points, provider, secret_field
from ab_sdk.notify import NotificationMessage, NotifierSettings


class Options(BaseModel):
    endpoint: str = Field("https://push.example.com", title="推送地址")
    key: str = secret_field(description="推送密钥")


class Pusher:
    def __init__(self, plugin: "MyPlugin", settings: NotifierSettings) -> None:
        self.plugin = plugin
        self.settings = settings

    async def send(self, message: NotificationMessage) -> bool:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.plugin.config.endpoint}/{self.plugin.config.key}",
                json={"title": message.title, "body": message.body},
            )
        return resp.is_success

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(NotificationMessage(kind="event", title="AB", body="测试"))
        return ok, "已发送" if ok else "发送失败"


class MyPlugin(Plugin[Options]):
    config_model = Options

    @provider(points.NOTIFIER, id="my-push")
    def push(self):
        return lambda settings: Pusher(self, settings)
```

启用插件后：

1. 设置 → 插件里会出现由 `Options` 自动生成的表单。`secret_field` 声明的字段以密码框显示，读取配置的接口只返回掩码。
2. 设置 → 通知 → 添加渠道时，类型下拉框会多出 `my-push`。

## 核心概念

### Plugin 与配置

- 继承 `Plugin[配置模型]` 并设置 `config_model`。AB 会按模型校验用户配置，插件通过 `self.config` 拿到带类型的实例。在 WebUI 保存不合法的值会被直接拒绝（HTTP 422）。
- `async setup()` 在加载后调用一次，`async teardown()` 在卸载前调用一次。配置变更时，插件会先 teardown，再重新构造并 setup。
- `self.ctx` 提供：
  - `log`：带 `plugin.<id>` 前缀的 logger
  - `kv`：插件私有的持久化键值存储，值须可 JSON 序列化
  - `data_dir`：`config/plugin-data/<id>/`
  - `bus`：事件总线

### 三种扩展声明

| 装饰器 | 用途 |
| --- | --- |
| `@provider(point, id=...)` | 工厂方法，返回该扩展点约定的实现 |
| `@hook(point, priority=...)` | 挂到宿主声明的 filter / transform 扩展点（后续版本开放） |
| `@subscribe(kind)` | 订阅事件，`"*"` 表示全部事件 |

扩展点名写错时，插件会加载失败并在插件列表里显示原因，不会被悄悄忽略。

### 隔离与熔断

- 钩子、事件处理和定时任务都有超时。
- 同一插件连续失败 5 次会被自动禁用，并在插件列表中显示原因。修改该插件的配置后会重新尝试加载。
- 插件发布的事件，`kind` 必须以 `<插件 id>.` 开头。

## 各扩展点

### 下载器

```python
from ab_sdk.downloader import AddResult, DownloaderCapabilities, DownloaderConnection


class MyClient:
    capabilities = DownloaderCapabilities(
        can_query=False, can_rename=False, can_manage=False, can_rss_rules=False
    )

    def __init__(self, conn: DownloaderConnection) -> None:
        self.conn = conn  # 来自设置页「下载器」的 host / username / password / ssl

    async def auth(self, retry: int = 3) -> bool: ...
    async def logout(self) -> None: ...
    async def add_torrents(self, torrent_urls, torrent_files, save_path, category, tags=None) -> AddResult: ...


class MyPlugin(Plugin):
    @provider(points.DOWNLOADER, id="my-client")
    def client(self):
        return MyClient
```

至少实现 `CoreDownloaderClient`（认证与添加种子）。需要重命名、整理等功能时，实现完整的 `DownloaderClient` 并在 `capabilities` 中声明，AB 会跳过未声明的操作。

### LLM 提供商

返回 `ab_sdk.llm.LLMProviderAdapter` 的子类，`@provider` 的 id 必须等于其 `info.id`。内置提供商的 id 不能被覆盖。

### 搜索站点

```python
from ab_sdk.search import SearchSite

@provider(points.SEARCH_SITE, id="my-site")
def site(self):
    return SearchSite(url="https://example.com/rss?q=%s", parser="tmdb")
```

用户在搜索设置里配置的同名站点优先。

### 定时任务

```python
from ab_sdk.tasks import ScheduledTask

@provider(points.SCHEDULED_TASK, id="sync")
def sync(self):
    async def run():
        ...
    return ScheduledTask(run, interval=lambda: self.config.interval, initial_delay=60)
```

任务与 RSS 刷新等内置任务一同启停，失败计入熔断。

### REST 路由

```python
from fastapi import APIRouter

@provider(points.API_ROUTER, id="api")
def api(self):
    router = APIRouter()

    @router.get("/stats")
    async def stats():
        return {"count": await self.ctx.kv.get("count", 0)}

    return router
```

- 路由挂载在 `/api/v1/plugins/<插件 id>/` 下，上例即 `GET /api/v1/plugins/my-plugin/stats`。
- **所有插件路由都强制登录鉴权**，与 WebUI 其它接口使用同一套凭据（会话 Cookie 或 `scope=api` 的 API 令牌）。插件无法注册匿名端点；未登录返回 401。
- 路由随插件启用出现、随停用消失，无需重启。同一插件可以提供多个 `API_ROUTER`，它们会合并到同一前缀下。
- 处理函数抛出 `HTTPException` 正常返回对应状态码；抛出其它异常返回 500，并计入熔断。
- 插件路由不出现在 `/docs` 的 OpenAPI 文档中。

### MCP 工具与资源

```python
from ab_sdk.mcp import McpResource, McpTool

@provider(points.MCP_TOOL, id="search")
def search_tool(self):
    async def handler(args: dict):
        return {"results": [...], "keyword": args["keyword"]}

    return McpTool(
        description="在私有站点搜索",
        handler=handler,
        input_schema={
            "type": "object",
            "properties": {"keyword": {"type": "string"}},
            "required": ["keyword"],
        },
    )

@provider(points.MCP_RESOURCE, id="stats")
def stats_resource(self):
    async def handler():
        return {"count": 3}

    return McpResource(name="统计", handler=handler)
```

- 对外名称自动加插件 id 前缀，避免冲突：工具名为 `<插件 id>__<id>`（双下划线），资源 URI 为 `autobangumi://plugins/<插件 id>/<id>`。不用 `.` 分隔，是因为不少 MCP 客户端会把工具名原样交给 LLM API，而后者通常只接受 `^[a-zA-Z0-9_-]{1,64}$`；不合规的工具名会被跳过并记录日志。
- 工具处理函数返回可 JSON 序列化的对象；资源处理函数返回字符串（原样返回）或可 JSON 序列化的对象。抛出的异常以 `{"error": "..."}` 返回给客户端，并计入熔断。工具默认超时 60 秒（`McpTool(timeout=...)`）。
- MCP 端点沿用 AB 的访问控制（IP 白名单或 `scope=mcp` 令牌），插件无需自行鉴权。

### 订阅系统事件

```python
from ab_sdk import subscribe
from ab_sdk.events import RssFailureEvent

@subscribe("rss_failure")
async def on_rss_failure(self, event: RssFailureEvent):
    self.ctx.log.warning("订阅 %s 失败：%s", event.rss_name, event.error)
```

AB 发出的、会进入通知中心的事件都是 `ab_sdk.events.SystemEvent` 的子类，带有 `severity`、`payload()`、`describe()`（默认中文标题与正文）和 `i18n()`（前端 i18n key 与参数）。它们先写入通知中心，再发布到事件总线，最后推送到外部通知渠道；关闭「通知」开关只影响外部推送，不影响插件收到事件。

| kind | 事件类 | 何时发布 |
| --- | --- | --- |
| `rss_failure` | `RssFailureEvent` | RSS 订阅从正常变为连接异常 |
| `download_failure` | `DownloadFailureEvent` | 种子重试后仍添加失败 |
| `offset_review` | `OffsetReviewEvent` | 番剧的季度 / 集数偏移需要人工确认 |
| `downloader_unavailable` | `DownloaderUnavailableEvent` | 下载器连不上、凭据错误或 IP 被封 |
| `update_available` | `UpdateAvailableEvent` | 检查到新版本 |
| `update_applied` / `update_failed` | `UpdateAppliedEvent` | 在线更新成功 / 失败（`kind` 随 `success` 变化） |
| `llm_auth_failure` | `LLMAuthFailureEvent` | 订阅类 LLM 提供商凭据失效 |
| `llm_plugin_install_failed` | `LLMPluginInstallFailedEvent` | LLM 插件安装失败 |
| `rename_conflict` | `RenameConflictEvent` | 媒体文件重命名遇到目标路径冲突 |
| `plugin.loaded` | `PluginLoaded` | 插件加载成功 |
| `plugin.disabled` | `PluginDisabled` | 插件加载失败或被熔断 |
| `inbox.changed` | — | 通知中心有新消息、已读或删除（宿主内部使用，供 SSE 推送） |

系统事件的 `kind` 沿用 3.x 的取值（通知中心按它存储和翻译），因此不带 `.` 前缀；插件自己的事件仍必须以 `<插件 id>.` 开头。后续版本会陆续增加流水线事件（如 `torrent.added`、`file.renamed`）。

### 通知文案模板

系统事件推送到外部渠道前，会依次经过 `message_template` 钩子。钩子拿到默认文案、事件和渠道类型，返回新的 `RenderedMessage` 即可改写，返回 `None` 表示不修改：

```python
from ab_sdk import hook, points
from ab_sdk.notify import RenderedMessage

@hook(points.MESSAGE_TEMPLATE)
def template(self, message: RenderedMessage, event, channel: str):
    if event.kind != "rss_failure":
        return None
    if channel == "telegram":
        return RenderedMessage(f"[告警] {message.title}", f"<b>{event.rss_name}</b>\n{event.error}")
    return None
```

- 只影响外部推送；通知中心里的文案由前端按 `i18n()` 渲染，不受影响。
- 钩子对每个启用的渠道各调用一次。钩子出错或超时时沿用上一步的文案，并计入熔断；返回值类型不对时整条消息回退到默认文案。
- 「新集数」通知暂不经过该钩子，仍使用通知渠道里配置的单集模板。

## 测试

`ab_sdk.testing` 可以在不启动 AB 的情况下构造并驱动插件：

```python
from ab_sdk.testing import create_plugin

async def test_push(tmp_path):
    plugin, ctx = create_plugin(MyPlugin, {"key": "k"}, data_dir=tmp_path)
    await plugin.setup()
    factory = plugin.push()
    ...
```

## 以 pip 包发布

在包的 `pyproject.toml` 中声明 entry point，并在**顶层包内**附带 `plugin.toml`：

```toml
[project.entry-points."autobangumi.plugins"]
my-plugin = "my_plugin:MyPlugin"
```

pip 安装的插件同样未签名，需要开启「允许未签名插件」。Docker 镜像无法 pip 安装，此时请使用本地目录，并把依赖放进 `vendor/`。
