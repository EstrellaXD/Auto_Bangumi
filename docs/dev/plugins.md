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

以及以下钩子（`@hook`，插件启用即生效）：

| 扩展点 | 常量 | 类型 | 用途 |
| --- | --- | --- | --- |
| `torrent.filter` | `points.TORRENT_FILTER` | filter | 决定已匹配规则的种子是否下载 |
| `title.parsed` | `points.TITLE_PARSED` | transform | 修正标题解析结果 |
| `torrent.adding` | `points.TORRENT_ADDING` | transform | 修改发给下载器的保存路径、分类、标签 |
| `http.request` | `points.HTTP_REQUEST` | transform | 修改 AB 发出的 GET 请求头（私有站 Cookie 等） |

此外，插件可以订阅事件（`@subscribe`），并使用私有的键值存储和数据目录。重命名等整理流水线的扩展点会在后续版本开放。

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
sdk = ">=0.3,<1"              # 依赖的 ab_sdk 版本范围
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

`request.kind` 区分番剧与电影，`request.torrent.homepage` 是种子的详情页。返回值是完整的新元数据，通常基于 `request.current` 修改。失败或超时时保留原值，并计入熔断。目前 WebUI 的订阅表单只提供内置取值，插件元数据源需要通过 API 设置订阅的 `parser` 字段。

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
