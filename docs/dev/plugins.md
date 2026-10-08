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
| 元数据源 | `points.METADATA_PROVIDER` | `MetadataProvider` | RSS 订阅的「解析器」 |
| REST 路由 | `points.API_ROUTER` | `fastapi.APIRouter` | 插件启用即生效 |
| MCP 工具 | `points.MCP_TOOL` | `McpTool` | 插件启用即生效 |
| MCP 资源 | `points.MCP_RESOURCE` | `McpResource` | 插件启用即生效 |
| 重命名方式 | `points.RENAME_STRATEGY` | `RenameStrategy` | 设置 → 番剧管理设置 → 重命名方式 |
| 文件分类 | `points.MEDIA_FILES` | `MediaFiles` | 暂只使用宿主实现（见下文） |
| 版本冲突策略 | `points.CONFLICT_POLICY` | `ConflictPolicy` | 暂只使用宿主实现（见下文） |

以及以下钩子（`@hook`，插件启用即生效）：

| 扩展点 | 常量 | 类型 | 用途 |
| --- | --- | --- | --- |
| `torrent.filter` | `points.TORRENT_FILTER` | filter | 决定已匹配规则的种子是否下载 |
| `title.parsed` | `points.TITLE_PARSED` | transform | 修正标题解析结果 |
| `torrent.adding` | `points.TORRENT_ADDING` | transform | 修改发给下载器的保存路径、分类、标签 |
| `http.request` | `points.HTTP_REQUEST` | transform | 修改 AB 发出的 GET 请求头（私有站 Cookie 等） |
| `message_template` | `points.MESSAGE_TEMPLATE` | transform | 改写系统事件推送到外部渠道的文案 |

此外，插件可以订阅系统事件与整理事件（`@subscribe`，如 `torrent.organized`），并使用私有的键值存储和数据目录。

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
sdk = ">=0.4,<1"              # 依赖的 ab_sdk 版本范围
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
| `@hook(point, priority=...)` | 挂到宿主声明的 filter / transform 扩展点 |
| `@subscribe(kind, timeout=...)` | 订阅事件，`"*"` 表示全部事件；`timeout` 覆盖默认 30 秒的单个事件处理超时 |

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

### 种子过滤（torrent.filter）

RSS 刷新时，种子先按规则匹配，再经过规则自带的「排除过滤」，最后交给 `torrent.filter` 钩子。任一钩子拒绝，该种子就不下载，也不会关联到番剧（与排除过滤相同）。手动「收集」整季时同样生效。

```python
from ab_sdk import Plugin, Verdict, hook, points
from ab_sdk.ingest import BangumiInfo, Release, TorrentInfo


class OnlyHevc(Plugin):
    @hook(points.TORRENT_FILTER, priority=50)
    def check(
        self, torrent: TorrentInfo, release: Release | None, bangumi: BangumiInfo
    ) -> Verdict:
        if "HEVC" in torrent.name or "x265" in torrent.name:
            return Verdict.ok()
        return Verdict.reject("不是 HEVC")
```

- `release` 是标题解析结果，无法解析时为 None。
- 钩子出错或超时按放行处理（fail-open），并计入熔断。
- 返回 `True` / `False` 也可以，但 `Verdict.reject(reason)` 的原因会写进日志。

内置插件「种子过滤」（`ingest-filters`）就是这样实现的：在 设置 → 插件 中填写「包含过滤」后，只有名称匹配的种子才会下载。

### 修正解析结果（title.parsed）

在确定性解析（以及启用时的 LLM 解析）之后、准入判定之前调用。收到冻结的解析结果，用 `dataclasses.replace` 返回修改后的副本；返回 None 表示不修改。返回其他类型会被忽略并计入熔断。

```python
from dataclasses import replace

ALIASES = {"LoliHouse": "Lolihouse"}


class GroupAlias(Plugin):
    @hook(points.TITLE_PARSED)
    def fix(self, release):
        if release.group in ALIASES:
            return replace(release, group=ALIASES[release.group])
        return None
```

新规则的番剧名、季度、字幕组都来自这里的结果，所以修改会影响新建的规则。改成 PV、合集等类型会让该资源不被收录。

### 修改添加请求（torrent.adding）

在种子交给下载器之前调用，参数是 `ab_sdk.ingest.AddRequest`：

```python
from dataclasses import replace


class Tagger(Plugin):
    @hook(points.TORRENT_ADDING)
    def tag(self, request):
        return replace(request, tags=(*request.tags, request.bangumi.official_title))
```

注意：

- 整理与重命名只处理 `Bangumi` 分类下的种子，修改 `category` 等于让 AB 不再整理这些种子。
- `ab:<番剧 id>` 标签用于重命名时定位番剧，钩子删掉它时 AB 会补回。
- 重命名会从保存路径的 `<番剧名>/Season N` 结构推断番剧与季度，修改 `save_path` 时请保留这一结构。

### 请求头（http.request）

AB 发出的 GET 请求（RSS、种子文件、站点页面）都会经过这个钩子，适合给私有站点加 Cookie 或换 User-Agent。只能修改请求头，`url` 与 `method` 的改动会被忽略。

```python
from ab_sdk import secret_field


class Options(BaseModel):
    cookie: str = secret_field(description="站点 Cookie")


class PrivateSite(Plugin[Options]):
    config_model = Options

    @hook(points.HTTP_REQUEST)
    def auth(self, request):
        if "pt.example.com" not in request.url:
            return None
        return replace(request, headers={**request.headers, "Cookie": self.config.cookie})
```

这个钩子在每个请求上都会调用，请保持轻量，不要在里面发起网络请求。

### 元数据源

新番规则入库前，AB 按 RSS 订阅的「解析器」取值选择元数据源，补全官方标题、季度、年份和海报。内置 `mikan` 与 `tmdb`，插件可以增加新的取值：

```python
from dataclasses import replace

from ab_sdk.ingest import Metadata, MetadataRequest


class BangumiTv:
    async def enrich(self, request: MetadataRequest) -> Metadata | None:
        info = await search(request.current.official_title)  # 自己的实现
        if info is None:
            return None  # 不修改
        return replace(request.current, official_title=info.name, poster_link=info.cover)


class MyPlugin(Plugin):
    @provider(points.METADATA_PROVIDER, id="bangumi-tv")
    def bgm(self):
        return BangumiTv()
```

`request.kind` 区分番剧与电影，`request.torrent.homepage` 是种子的详情页。返回值是完整的新元数据，通常基于 `request.current` 修改。失败或超时时保留原值，并计入熔断。添加订阅时，「解析器」下拉框会列出插件提供的元数据源。

### 重命名方式（rename_strategy）

下载完成后，AB 为种子里的每个正片与字幕调用设置项「重命名方式」（`bangumi_manage.rename_method`）对应的 Provider。宿主只自带 `none`（保留原名）；`pn`、`advance` 与 `template` 由内置插件「重命名」（`rename`，默认启用）提供。插件登记的 id 会出现在 设置 → 番剧管理设置 → 重命名方式 的下拉框里。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.rename import RenameInput, RenameSkipped, pad


class JellyfinStyle:
    def target_name(self, f: RenameInput) -> str:
        language = f".{f.language}" if f.kind == "subtitle" else ""
        if f.episode_type == "movie":
            return f"{f.bangumi_name}{language}{f.suffix}"
        if not f.bangumi_name:
            raise RenameSkipped("缺少番剧文件夹名")
        return f"{f.bangumi_name} - S{pad(f.season)}E{pad(f.episode)}{language}{f.suffix}"


class MyRename(Plugin):
    @provider(points.RENAME_STRATEGY, id="jellyfin-style")
    def jellyfin(self):
        return JellyfinStyle()
```

- `RenameInput` 是冻结快照：`kind`（`media` / `subtitle`）、`media_path`（种子内原相对路径）、`title`（解析自文件名）、`bangumi_name`（保存目录的番剧文件夹名）、`season`、`episode`（已应用集数偏移）、`suffix`（含点）、`episode_type`（`episode` / `movie` / `special`）、`language`（字幕语言）、`group`。字幕不再有单独的 `subtitle_*` 方式，按 `kind` 区分。
- 返回种子内的新相对路径，通常只是文件名（扩展名与字幕语言由策略自己拼上）；返回 `f.media_path` 表示不改名。`pad(n, width=2)` 补零且保留半集的小数（`pad(9.5) == "09.5"`）。
- 抛出 `RenameSkipped(原因)`：该文件保留原名，种子不打「已重命名」标签，每个种子按原因发一条 `rename_skipped` 通知；修正后下一轮自动重试。它表示输入或配置有问题，不计入熔断。
- 抛出其它异常、返回空串或非字符串：同样保留原名并通知，同时计入熔断。
- `target_name` 是同步调用，没有超时，请不要在里面做网络或磁盘 IO。
- 设置里选择的 id 没有登记（如插件被停用或熔断）时，AB 记录一次日志并按 `none` 处理。

内置的 `template` 使用 Jinja2 沙箱模板渲染文件名主体，在 设置 → 插件 → 重命名 中填写，例如 `{{ title }} - S{{ season|pad(2) }}E{{ episode|pad(2) }}`。可用变量为 `title`、`bangumi_name`、`season`、`episode`、`episode_type`、`group`、`kind`、`language`。保存时会编译并试渲染一次，不合法的模板直接被拒绝（HTTP 422）。运行时渲染失败或结果为空、含路径分隔符时，该文件保留原名并通知，不会退回 `pn`。

### 文件分类与版本冲突（media_files / conflict_policy）

- `media_files`：`classify(path) -> "media" | "subtitle" | "ignore"`，决定种子内哪些文件按正片、字幕重命名。宿主实现按扩展名判断（`.mp4` / `.mkv` 为正片，`.ass` / `.srt` 为字幕）。
- `conflict_policy`：`decide(ConflictRequest) -> ConflictDecision("hold" | "replace")`，新种子的规范文件名已被另一个种子占用时决定保留旧的还是替换。宿主实现沿用设置项「版本冲突策略」。宿主只在「唯一占用者、双方都是单文件种子、双方解析身份完整」时执行替换，其它情况一律按 `hold` 处理。

这两个扩展点目前只使用宿主实现（id 为 `default`）。插件可以登记自己的实现，但要等多下载器版本的 `plugins.slots` 提供后才能被选用。

### 整理事件（file.renamed / torrent.organized）

| kind | 事件类 | 字段 | 何时发布 |
| --- | --- | --- | --- |
| `file.renamed` | `FileRenamed` | `bangumi_id`、`old_path`、`new_path`、`file_kind`、`downloader_id` | 一个文件被实际重命名（含版本替换后的改名） |
| `torrent.organized` | `TorrentOrganized` | `torrent_hash`、`bangumi_id`、`files`（`OrganizedFile(path, kind)` 元组）、`downloader_id` | 一个种子整理完成；重命名方式为 `none` 时同样发布，`files` 为原路径 |

- 路径是**下载器视角**的绝对路径，保存目录与种子内路径以 `/` 拼接（Windows 下载器的 `\` 也统一为 `/`）。AB 与下载器看到的目录不同（如分别运行在不同容器）时，订阅者需要自己做路径映射。
- `bangumi_id` 来自种子的 `ab:<id>` 标签，旧种子可能为 None。`downloader_id` 目前固定为 `"default"`，多下载器版本会给出实例 id。
- `torrent.organized` 的投递是**至少一次**：未打「已重命名」标签的种子（如重命名方式为 `none`）在每次 AB 重启后会再发布一次，订阅者必须幂等。
- 这两个事件只发布到事件总线，不进入通知中心。

```python
from ab_sdk import subscribe
from ab_sdk.events import TorrentOrganized

@subscribe("torrent.organized", timeout=600)
async def on_organized(self, event: TorrentOrganized):
    for f in event.files:
        if f.kind == "media":
            await self.refresh_library(f.path)
```

### 内置插件：硬链接到媒体库（hardlink）

内置插件 `hardlink` 默认停用，在 设置 → 插件 中启用。它订阅 `torrent.organized`，把正片与字幕链接到媒体库目录，下载目录原样保留继续做种。

| 选项 | 说明 |
| --- | --- |
| `source_root` | 下载根目录（AB 本地路径）。媒体库保持与它相同的目录结构：`library_root / (文件相对 source_root 的路径)` |
| `library_root` | 媒体库目录（AB 本地路径），不能位于 `source_root` 内 |
| `path_map` | `[{downloader, from, to}]`：把下载器路径前缀 `from` 换成 AB 本地路径 `to`。`downloader` 默认为 `default`；按最长前缀匹配，未匹配的路径原样使用 |
| `cross_device` | 硬链接遇到跨文件系统（EXDEV）时：`copy`（默认，复制文件）、`symlink`（创建软链接）、`skip`（跳过并通知） |

- 媒体库中已有同名文件、但不是本插件创建的：跳过，不覆盖，并为该种子发一条 `hardlink.failed` 通知。
- 本插件之前为同一集创建的链接，在版本升级（新版本替换旧种子，规范文件名不变）后会被原子替换为指向新文件的链接。
- 已链接的文件再次收到事件时不做任何事；插件在自己的键值存储里记录它创建过的目标路径。
- **删除种子不会删除媒体库中的链接**。
- 启用前已经下载的文件不会自动处理。调用 `POST /api/v1/plugins/hardlink/backfill` 按需补链：遍历 `source_root` 下的 `.mp4` / `.mkv` / `.ass` / `.srt`，返回 `{"linked", "exists", "conflict", "failed"}` 计数。设置页里的「补链已有文件」按钮将随前端插件挂载点一起提供。

::: tip Docker
硬链接不能跨文件系统。在 Docker 中，请把下载目录与媒体库放在同一块盘上，并以**同一个挂载点**映射进 AB 容器（例如把 `/mnt/media` 整体挂载为 `/media`，下载目录与媒体库都在其下），否则两个独立挂载的目录即使在同一块盘上，也会被视为不同文件系统，链接会退化为 `cross_device` 指定的行为。下载器运行在另一个容器里、看到的路径与 AB 不同时，用 `path_map` 做映射。
:::

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
| `rename_skipped` | `RenameSkippedEvent` | 重命名方式无法为种子中的文件给出名字，文件保留原名 |
| `plugin.loaded` | `PluginLoaded` | 插件加载成功 |
| `plugin.disabled` | `PluginDisabled` | 插件加载失败或被熔断 |
| `inbox.changed` | — | 通知中心有新消息、已读或删除（宿主内部使用，供 SSE 推送） |

系统事件的 `kind` 沿用 3.x 的取值（通知中心按它存储和翻译），因此不带 `.` 前缀；插件自己的事件仍必须以 `<插件 id>.` 开头。整理流水线事件 `file.renamed`、`torrent.organized` 见上文「整理事件」。

插件也可以继承 `SystemEvent` 定义自己的可通知事件。用 `self.ctx.bus.publish(...)` 发布后，它与宿主事件走同一条路径：写入通知中心（前端没有对应翻译时显示 `describe()` 的标题与正文），发布到事件总线，再推送到外部通知渠道。`dedup_key()` 相同的事件在通知中心合并为一条。内置插件 `hardlink` 的 `hardlink.failed` 就是这样发出的。

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
