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

此外，插件可以订阅事件（`@subscribe`），并使用私有的键值存储和数据目录。RSS 过滤、重命名等流水线扩展点会在后续版本陆续开放。

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
