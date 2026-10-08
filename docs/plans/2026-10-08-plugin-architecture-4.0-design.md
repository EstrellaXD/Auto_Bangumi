# AutoBangumi 4.0 插件化重构设计

> 状态：草案（核心决策已确认）· 目标分支：`4.0-dev` · 基线：`main@3.3.6`

## 0. 已确认决策

| 议题 | 决策 |
|---|---|
| 升级路径 | 4.0 **只支持从 3.3.x 升级**，3.0 / 3.1 / 3.2 兼容层全部删除（第 8.3 节） |
| SDK 版本 | `ab_sdk` 在 4.0 期间为 `0.x`，允许破坏性调整；4.1 冻结 `1.0`，此后严格 semver |
| 插件依赖 | 允许 `vendor/` 自带**纯 Python** 依赖，禁止 C 扩展；不做运行时 pip 安装 |
| 按订阅选择下载器 | **纳入 4.0**（第 3.5 节） |
| 前端插件组件 | **纳入 4.0**（第 3.8 节） |
| pip entry point 来源 | **纳入 4.0**（第 2.4 节） |
| 插件 REST 路由 / MCP 工具 | **纳入 4.0**（第 3.9 节） |

### 实施中的调整（P2）

- **内置实现以 `core` 身份登记**。qB / aria2 / mock 下载器和各通知渠道，与第三方插件使用同一个扩展注册表和同一套 `ab_sdk` 契约。区别是它们由宿主直接登记，不经插件管理器加载，因此不能被禁用，也不会因插件故障被熔断。LLM 内置适配器与预设仍由原 LLM 注册表管理，插件适配器作为第三个来源并入。
- **内置实现的配置不迁移**。`downloader.type`、`notification.providers[].type`、`llm.provider` 直接作为 Provider id 查找。第 4.4 节的 `slots` / `instances` 与第 9 节的配置迁移器暂不实施，P2.5 多下载器时再统一设计。
- **扩展点改名**：`search_provider` 改为 `search_site`，以区分用户在搜索设置里维护的站点列表。
- 签名目录来源（LLM 安装器泛化）、`dev_mode` 文件监听、bark / wecom 旧字段别名清理，移到 P7（生态）。

## 1. 背景与目标

AB 目前只有 **LLM 提供商** 是真正的运行时插件系统：签名下载、目录加载、懒导入、热重载。
其余能定制的行为都是静态字典、`if/elif` 或配置里的 `Literal`。

| 现有扩展点 | 现状 | 选择方式 |
|---|---|---|
| LLM 提供商 | `BUILTIN` + `PRESET_ADAPTERS` + `config/plugins` 签名插件 | `llm.provider` |
| 通知 | 静态 `PROVIDER_REGISTRY` 字典 | `notification.providers[].type` |
| 下载器 | `download_client.py:150` if/elif（qb/aria2/mock） | `downloader.type` |
| 搜索站点 | `config/search_provider.json` 数据 | 站点 key |
| 元数据（mikan/tmdb） | `rss/analyser.py` if/elif | `RSSItem.parser` |
| 标题解析引擎 | `selector.py` if/else | `rss_parser.engine` |
| 重命名方式 | `renamer.py:132` if/elif | `bangumi_manage.rename_method` |
| 版本冲突策略 | 内联在 `renamer.py:1459` | `revision_conflict_policy` |
| 定时任务 | `AppContext.build()` 固定列表 | 不可配置 |
| 系统事件 | `SystemEvent` 封闭 Union | 不可扩展 |
| MCP 工具 / 资源 | 静态列表 + if/elif | 不可扩展 |

用户想定制的东西，比如自定义重命名格式、包含过滤、入库后硬链接或刷新 Jellyfin、私有 RSS 站点、新的下载器，现在只能 fork 改源码。

**目标**

1. 所有「用户可能想换掉或追加」的行为都变成**扩展点**，内置实现本身也是插件（自举 / dogfooding）。
2. 提供**稳定、版本化的插件 SDK**（`ab_sdk`），与内部实现解耦。内部重构不应破坏第三方插件。
3. 插件可声明配置 schema，WebUI **自动渲染**配置表单，无需改前端；需要自定义界面时可提供前端组件（第 3.8 节）。
4. 插件崩溃或超时**不拖垮主流程**：隔离、熔断、自动禁用。
5. 借大版本窗口**清理死代码与 3.x 兼容层**（见第 8 节）。

**非目标**

- 不做进程级沙箱。插件与 AB 同进程、同权限，信任靠「签名目录 + 用户显式允许本地插件」。
- 不改 qB/aria2 的外部 API 语义。

## 2. 核心概念

### 2.1 两类扩展：Provider 与 Hook

| 类型 | 语义 | 例子 |
|---|---|---|
| **Provider（槽位）** | 某个能力的一个可选实现，按 id 选择 | 下载器、重命名策略、元数据源、标题解析引擎 |
| **Hook（钩子）** | 在流水线某点插入逻辑，可多个、按优先级串联 | 种子过滤、入库后处理、事件订阅 |

Hook 再细分三种：

- **Filter hook** 返回 `accept / reject(reason)`，任一 reject 即短路。
- **Transform hook** 接收并返回修改后的上下文，用于改写标题或路径。
- **Observer hook** 只订阅事件（`@subscribe`），异步执行，失败不影响主流程。

### 2.2 插件包结构

```
my-plugin/
├── plugin.toml          # 清单
├── my_plugin/
│   ├── __init__.py      # 导出 Plugin 子类
│   └── ...
└── README.md
```

```toml
# plugin.toml
[plugin]
id = "hardlink-organizer"        # 全局唯一，[a-z0-9-]
name = "硬链接整理"
version = "1.2.0"
sdk = ">=4.0,<5"                 # 依赖的 ab_sdk 版本范围（替代 min_ab_version）
entry = "my_plugin:HardlinkPlugin"
authors = ["..."]
description = "..."

[plugin.requires]
python = []                      # 额外 pip 依赖（仅 pip/开发模式允许，见 2.4）
permissions = ["fs.write", "downloader.read"]   # 声明式，展示给用户，见 6.2
```

### 2.3 插件入口：一个类注册多个扩展

```python
from ab_sdk import Plugin, Verdict, hook, provider, subscribe
from ab_sdk.rename import RenameStrategy, RenameInput   # P4 提供
from ab_sdk.events import FileRenamed                   # P4 提供
from pydantic import BaseModel

class Config(BaseModel):
    target_root: str = "/media/anime"
    mode: Literal["hardlink", "symlink", "copy"] = "hardlink"

class HardlinkPlugin(Plugin):
    config_model = Config                     # 自动生成 WebUI 表单；self.ctx.config 为校验后的实例

    async def setup(self): ...                # 生命周期：加载 / 配置变更后重建
    async def teardown(self): ...

    @subscribe("file.renamed")                # Observer：事件订阅，独立队列异步执行
    async def link(self, event: FileRenamed): ...

    @hook("torrent.filter", priority=50)      # Filter / Transform：必须是宿主声明的扩展点
    def only_hevc(self, torrent, release) -> Verdict: ...

    @provider("rename_strategy", id="jellyfin-style")   # Provider：工厂方法，返回实现对象
    def jellyfin(self) -> RenameStrategy:
        return JellyfinRename(self.ctx.config)
```

Observer 用独立的 `@subscribe` 而不是 `@hook`：`@hook` 只接受已声明的 filter / transform 扩展点，写错名字会在加载时报「未知扩展点」，而不是悄悄变成一个永远收不到事件的订阅。

不使用 pluggy：它是同步模型，而 AB 全异步，且需要类型化的上下文与超时控制。
采用自研的轻量类型化注册表，实现集中在 `module/plugin/registry.py`。

### 2.4 插件来源与发现

按优先级从高到低：

1. **内置**：`module/plugins/builtin/<id>/`，随镜像发布，不可卸载但可禁用。
2. **签名目录**：泛化现有 `llm_plugins/installer.py`。
   - 目录 tag 从 `llm-plugins` 改为 `plugins`，`catalog.json` 增加 `kind` / `extension_points` 字段。
   - 保留 ed25519 签名、sha256、zip-slip 防护、版本指针 `installed.json`、带版本号的模块名热加载。
3. **本地目录**：`config/plugins/local/<id>/`，用于用户二次开发。
   - 默认关闭。需开启 `plugins.allow_unsigned = true`。
   - WebUI 显示「未签名」警告。
   - 开启开发模式（`plugins.dev_mode`）后监听文件变更，自动热重载。
4. **pip entry point**：`[project.entry-points."autobangumi.plugins"]`。
   - 面向非 Docker 部署和插件作者本地测试。
   - 依赖由用户的 pip 环境负责，AB 只校验 `sdk` 版本范围。

**依赖规则**（适用于签名目录与本地目录两种来源）：

- 插件可在 `vendor/` 目录自带纯 Python 依赖。加载时把 `vendor/` 以插件私有前缀插入模块搜索路径，避免与宿主或其他插件的同名包冲突。
- 禁止 C 扩展。`ab-plugin validate` 和安装器都要拒绝 `.so` / `.pyd` 文件。
- 不做运行时 pip 安装：Docker 镜像保持不可变，也不扩大攻击面。
- 宿主已有的依赖（httpx、pydantic、Jinja2 等）在 SDK 文档中列为「可直接使用」，并随 SDK 主版本保证存在。

同一 id 只能来自一个来源，冲突时以高优先级为准并告警。

## 3. 扩展点清单

接口签名为 SDK 草案。「现状」列给出要拆出的代码位置（相对 `backend/src/module/`）。

### 3.1 来源 / 抓取（Source）

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `feed_source` | Provider | `fetch(feed: FeedConfig) -> list[RawItem]` | `network/request_contents.py:15` + `network/site/mikan.py:6`（唯一的通用 RSS 解析） |
| `search_provider` | Provider | `build_query(keywords) -> FeedConfig`；`parse(...)` | `conf/search_provider.py` 数据 + `searcher/provider.py` |
| `http.request` | Transform hook | 修改请求头、cookie、UA，用于私有站或 PT | `network/request_url.py:112` 硬编码 UA |

`feed_source` 按 `FeedConfig.source`（替代当前语义混乱的 `RSSItem.parser`）选择，默认是 `rss2`。
内置提供 `rss2`、`mikan`、`dmhy`、`nyaa`、`anibt`：前者是通用实现，后几个负责站点特有字段（homepage、发布组、大小）。
搜索站点 JSON 配置保留，作为 `generic-search` 内置插件的配置。

### 3.2 解析（Parse）

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `title_parser` | Provider | `parse(raw: str) -> ParsedRelease \| None` | `parser/analyser/selector.py`（classic / tokenizer） |
| `title.parsed` | Transform hook | 修正 `ParsedRelease`（字幕组别名、季数修正规则） | 无 |
| `llm_provider` | Provider | 现有 `LLMProviderAdapter` 原样迁入 SDK | `parser/analyser/providers/` |
| `file_parser` | Provider | `parse(path, ctx) -> EpisodeFile \| SubtitleFile` | `parser/analyser/torrent_parser.py`（`RULES`、`SUBTITLE_LANG`） |
| `admission_policy` | Provider | `target(release) -> bangumi \| movie \| None` | `parser/release_policy.py:53` |

LLM 的 `primary` / `fallback` 编排变成 `title_parser` 的一种**组合**：内置 `chain` 解析器，按配置顺序尝试多个解析器。
`ParserEngine` Literal 改为注册表 id。

### 3.3 匹配 / 过滤 / 决策（Match）

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `torrent.filter` | Filter hook | `accept(torrent, release, bangumi) -> Verdict` | `rss/engine.py:165`（只有 exclude 正则） |
| `bangumi_matcher` | Provider | `match(torrent, release, rules) -> Bangumi \| None` | `database/bangumi.py:151` |
| `release_ranker` | Provider | `score(release, bangumi) -> tuple` | `rss/engine.py:44` + `_select_preference_skips` |
| `rule.created` | Transform hook | 新番规则入库前修改或拒绝 | `rss/analyser.py:108` + `database/bangumi.py:106` |

内置 `torrent.filter` 拆为三项：`exclude-regex`（现有行为）、新增 `include-regex`、新增 `size-limit`。
都可按订阅单独覆盖。按订阅配置挂在 `Bangumi.plugin_options: JSON` 新列上。

### 3.4 元数据（Enrich）

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `metadata_provider` | Provider（可链） | `enrich(item, hint) -> MetadataPatch` | `rss/analyser.py:25-97` if/elif；`mikan_parser.py`、`tmdb_parser.py` |
| `calendar_provider` | Provider | `fetch() -> list[CalendarItem]`；`match(bangumi, items)` | `parser/analyser/bgm_calendar.py` |
| `offset_advisor` | Provider | `suggest(bangumi, info, latest_ep) -> OffsetSuggestion \| None` | `parser/analyser/offset_detector.py` |
| `poster_provider` | Provider | `fetch(bangumi) -> bytes \| url` | 分散在 mikan / tmdb |

`metadata_provider` 以链式执行，前一个结果作为 hint 传给下一个，例如先 mikan 再 tmdb 补全年份和海报。
后续可加 Bangumi.tv、AniList 等插件。
TMDB 常量（genre 16、`w780`、`gap_months=6`）收进插件配置。

### 3.5 下载（Download）

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `downloader` | Provider | 现有 `DownloaderClient` Protocol + `DownloaderCapabilities` | `downloader/download_client.py:150` |
| `save_path` | Provider | `save_path(item) -> str`；`parse_save_path(path) -> (name, season)` | `downloader/path.py:91`、`:54` |
| `torrent.adding` | Transform hook | 修改 category、tag、save_path、暂停状态 | `download_client.py:424`（硬编码 `"Bangumi"`、`ab:<id>`） |

**按订阅选择下载器**：下载器改为**多实例**。

- `plugins.instances` 中可配置多个下载器实例（如 `qb-main`、`aria2-nas`），其中一个设为默认。
- `Bangumi`、`Movie` 新增 `downloader_id` 列。为空时用默认实例。RSS 订阅也可设默认下载器，新规则继承。
- `torrent` 表记录实际使用的 `downloader_id`，重命名、删种、offset 查找按此路由。
- organize 流水线**逐实例**拉取已完成种子。某个实例不可用只跳过该实例，并发布 `DownloaderUnavailable(instance)` 事件。
- 现有 `ab:<id>` tag、`Bangumi` category 语义保持不变，在各实例内独立。
- `_client_cache` 从「单个设置 key」改为按实例 id 缓存。凭证闩锁、引用计数也按实例隔离。

下载器工厂统一为 `create(config: PluginConfig) -> DownloaderClient`。
这样可以消除各后端构造参数不一致的问题。
缓存、引用计数、凭证闩锁留在 facade 中，与具体后端无关。

### 3.6 整理 / 重命名（Organize）

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `rename_strategy` | Provider | `target_name(f: RenameInput) -> str` | `manager/renamer.py:113-167` |
| `media_files` | Provider | `classify(path) -> media \| subtitle \| ignore` | `downloader/path.py:22`（仅 mp4/mkv/ass/srt）、`is_ep` 深度 ≤ 2 |
| `conflict_policy` | Provider | `decide(owner, incoming, files) -> hold \| replace` | `manager/revision_policy.py` + `renamer.py:1441` |
| `file.renamed` | Observer hook | `(bangumi, old_path, new_path, file_kind)` | 无 |
| `torrent.organized` | Observer hook | 整个种子处理完成 | 无 |

内置 `rename_strategy` 包括 `pn`、`advance`、`none`，并新增 `template`：
- `template` 使用 Jinja2 沙箱模板，例如 `{{ title }} - S{{ season|pad(2) }}E{{ episode|pad(2) }}`。项目已依赖 Jinja2，能覆盖 80% 的定制需求。
- 字幕不再是 `subtitle_*` 平行方法，改为 `RenameInput.kind`。
- 删除废弃的 `normal`。

`file.renamed` 是最大的新增价值点，可接硬链接、NFO、Jellyfin/Plex/Emby 刷新、rclone 上传。
内置先提供 `media-server-refresh` 示例插件。

`renamer.py` 共 1856 行，借此拆分：
- 编排（拉列表、查 offset、调用策略）
- 策略（插件）
- revision 替换事务（`manager/revision_saga.py`）

### 3.7 通知 / 事件（Notify）

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `notifier` | Provider（多实例） | `send(message: RenderedMessage)`；`test()` | `notification/providers/*` + 静态 `PROVIDER_REGISTRY` |
| `message_template` | Transform hook | 针对事件类型渲染 title / body | `notification/base.py:89`（只有 4 个变量） |
| 任意事件 | Observer hook | 见 4.2 | — |

`NotificationProvider` 配置从「所有字段的大并集」改为每个插件自己的 `config_model`。

### 3.8 前端组件（WebUI 扩展）

方案采用 **Web Component**，不用 iframe。理由：插件后端本就与 AB 同进程、同信任级别，iframe 隔离带来的安全收益有限，主题、尺寸和通信的成本却很高。

- 插件可在 `web/` 目录提供已构建的 ES module，在其中定义 custom element（如 `<ab-plugin-manual-pick>`）。宿主通过 `/api/v1/plugins/<id>/web/<file>` 提供这些文件，需要鉴权。
- 清单声明挂载点：

  ```toml
  [[plugin.ui]]
  slot = "bangumi.detail.tab"    # 番剧详情页标签
  element = "ab-plugin-manual-pick"
  entry = "web/index.js"
  title = { zh-CN = "手动选种", en-US = "Manual pick" }
  ```

- 初始挂载点：
  - `settings.section`：设置页分区，替代或补充 JSON Schema 表单
  - `bangumi.detail.tab`：番剧详情页标签
  - `bangumi.card.action`：番剧卡片操作菜单
  - `page`：侧边栏独立页面，路由 `/plugins/<id>`
  - `dashboard.widget`：首页小组件
- **宿主桥接**：组件只通过注入的 `host` 对象与宿主交互，不直接用全局 axios 或 store。

  ```ts
  interface AbHost {
    pluginId: string
    api: { get, post, put, delete }   // 自动带鉴权，限定 /api/v1/plugins/<id>/ 前缀与公开只读 API
    i18n: { locale: string; t(key: string): string }
    theme: { mode: 'light' | 'dark'; tokens: Record<string, string> }  // CSS 变量
    toast(msg: string, kind?: 'info' | 'error'): void
    events: { on(kind: string, cb): () => void }  // 订阅 SSE 事件总线
  }
  ```

- 组件以 Shadow DOM 渲染，主题通过 CSS 变量下发。
- 加载失败或抛错由宿主的错误边界兜住：只显示「插件组件加载失败」，不影响页面其余部分。
- 安全：
  - 组件运行在主站 origin，等同于可以执行任意 JS。签名目录插件随包签名，本地插件沿用 `allow_unsigned` 门控。
  - UI 资源只从插件目录读取，CSP 禁止远程脚本。
- 提供 `@autobangumi/plugin-ui` npm 包：`AbHost` 类型定义、主题 CSS 变量、基础样式，以及 Vite 库模式模板。

### 3.9 调度 / API / MCP

| 扩展点 | 类型 | 接口 | 现状 |
|---|---|---|---|
| `scheduled_task` | Provider | `ScheduledTask(name, interval(), enabled(), run(ctx))` | `core/context.py:116` 固定列表；间隔常量在 `:50` |
| `api_router` | Provider | 返回 `APIRouter`，挂载于 `/api/v1/plugins/<id>/` | `api/__init__.py` 静态 include |
| `mcp_tool` / `mcp_resource` | Provider | `Tool` 定义 + handler | `mcp/tools.py:216`、`mcp/resources.py:56` if/elif |

现有 rss / rename / offset_scan / calendar / update_check 都注册为内置 `scheduled_task`。
间隔可配，修复「6h / 24h 不可改」的问题。
新增内置 `metadata_refresh` 任务：`refresh_metadata` 当前只能通过 API 触发。

## 4. 运行时架构

### 4.1 模块布局

```
backend/src/
├── ab_sdk/                  # 稳定公开 API（仅类型、Protocol、基类、装饰器、事件）
│   ├── __init__.py          # Plugin, hook, provider, PluginContext
│   ├── models.py            # ParsedRelease, Bangumi(只读视图), RawItem, ...
│   ├── events.py
│   ├── source.py / parse.py / match.py / download.py / rename.py / notify.py ...
│   └── testing.py           # FakeContext、契约测试套件
└── module/
    ├── plugin/              # 运行时：发现、加载、注册表、生命周期、隔离
    │   ├── manifest.py
    │   ├── loader.py        # 由 llm_plugins/loader.py 泛化
    │   ├── installer.py     # 由 llm_plugins/installer.py 泛化
    │   ├── registry.py      # ExtensionRegistry：providers + hooks
    │   ├── runner.py        # 调用 hook：优先级、超时、熔断
    │   ├── bus.py           # EventBus
    │   └── config.py        # 插件配置存取 + JSON Schema
    ├── plugins/builtin/     # 全部内置实现（qb、aria2、tmdb、mikan、pn、telegram ...）
    └── pipeline/            # 流水线编排（只调用扩展点，不含具体策略）
        ├── ingest.py        # Source → Parse → Match → Download
        └── organize.py      # 完成种子 → 分类 → 重命名 → 后处理
```

**依赖方向**是 `ab_sdk` ← `module.plugins.*` ← `module.pipeline` ← `module.api/core`。
`ab_sdk` 不得 import `module.*`。用 import-linter 架构测试强制，对应 07-09 设计文档提出的「架构测试」。

### 4.2 事件总线

替换封闭的 `SystemEvent` Union 和 producer 返回事件列表的模式：

```python
bus.publish(TorrentAdded(bangumi_id=..., name=...))
```

- 事件是 `ab_sdk.events` 中的冻结 dataclass，保留现有 `kind / severity / once / dedup_key / describe`。插件可以定义并发布自己的事件，以 `<plugin-id>.` 为前缀。
- 订阅者包括：通知管理器（替代 `send_event`）、inbox 记录、SSE 推送（替代 `api/events.py` 的 1s 轮询 + `inbox_revision`）、插件 observer hook。
- 投递是 `asyncio` 队列 + 每订阅者独立 task，单个订阅者的异常和超时被隔离。
- 新增事件：`feed.fetched`、`torrent.added`、`torrent.completed`、`file.renamed`、`rule.created`、`rule.archived`、`settings.reloaded`。

### 4.3 PluginContext（插件可见的能力）

插件**只**通过 `ctx` 访问宿主，不 import `module.*`：

```python
class PluginContext(Protocol):
    plugin_id: str
    config: BaseModel                         # 已校验的插件配置
    log: logging.Logger                       # 前缀 [plugin:<id>]
    http: HttpClient                          # 共享代理 / UA / 重试
    bus: EventBus
    kv: KeyValueStore                         # 插件私有持久化（plugin_kv 表）
    secrets: SecretStore                      # 由 llm CredentialStore 泛化
    data_dir: Path                            # config/plugin-data/<id>/
    bangumi: BangumiReadAPI                   # 只读查询 + 有限写操作
    downloader: DownloaderFacade
```

数据库 session **不暴露**给插件：遵守「session per operation」约定，插件也不应持有 ORM 对象。

### 4.4 配置

```jsonc
// config.json
{
  "plugins": {
    "allow_unsigned": false,
    "dev_mode": false,
    "enabled": { "hardlink-organizer": true },
    "options": { "hardlink-organizer": { "target_root": "/media" } },
    "slots": {                                // Provider 选择
      "downloader": "qbittorrent",
      "rename_strategy": "pn",
      "title_parser": ["tokenizer", "llm"],   // 链
      "metadata_provider": ["mikan", "tmdb"]
    },
    "hook_order": { "torrent.filter": ["exclude-regex", "include-regex"] }
  }
}
```

- 多实例插件（多个 Telegram、多个下载器）用 `instances: [{id, plugin, options, default?}]`。`slots.downloader` 指向默认下载器实例 id。
- `GET /api/v1/plugins` 返回每个插件的 `config_model.model_json_schema()`。前端用通用 JSON Schema 表单组件渲染，`config-notification.vue` 等专用页面逐步退化为通用表单。
- 秘密字段用 `Field(json_schema_extra={"secret": True})` 标注，读 API 不返回，沿用现有「不回传 secret」规则。
- `AppContext.reload_settings()` 改为：重新校验插件配置，并对受影响插件调用 `teardown` + `setup`。现在在 `context.py:405` 显式 import 的各种 `reset_cache()` 改为插件在 `settings.reloaded` 事件中自行处理。

### 4.5 隔离与可靠性

- 每次 hook / provider 调用都有超时（默认 30s，可在清单里声明）。
- 每个插件有熔断器：连续 N 次失败后自动禁用，并发布 `PluginDisabled` 事件进入 inbox。复用 LLM 熔断实现。
- Provider 失败的处理：
  - Filter 默认 **fail-open**（不过滤），可配置为 fail-closed。
  - 下载器、重命名失败沿用现有「跳过并记录」语义。
- 加载失败（导入错误、SDK 版本不符、清单无效）只禁用该插件，不阻止启动。WebUI 显示原因。

## 5. 流水线重写

`rss/engine.py` 的 `_refresh_rss` 和 `manager/renamer.py` 的 `rename` 改写为显式阶段，每阶段只调用扩展点：

```
ingest:  feed_source.fetch → http.request(hook)
       → title_parser(chain) → title.parsed(hook) → admission_policy
       → bangumi_matcher → torrent.filter(hooks) → release_ranker
       → [新标题] metadata_provider(chain) → rule.created(hook)
       → save_path → torrent.adding(hook) → downloader.add
       → bus: torrent.added

organize: downloader.completed → media_files.classify → file_parser
        → offset 查找 → rename_strategy → conflict_policy
        → downloader.rename → bus: file.renamed → torrent.organized
```

`parser_engine_snapshot()` 的「一次工作流固定一个引擎」语义，改为在流水线入口快照 slot 配置。

## 6. 安全模型

### 6.1 信任分级

| 来源 | 默认 | 说明 |
|---|---|---|
| 内置 | 启用 | 随镜像签发 |
| 签名目录 | 需用户点「安装」 | 沿用 ed25519 校验 |
| 本地目录 / pip | **默认拒绝** | 需开启 `allow_unsigned`，UI 持续显示警告 |

### 6.2 权限声明

`permissions` 只做**告知**，不做强制（同进程无法强制），在安装确认框中展示。
例外是 `ctx` 层的有限能力门控，例如没声明 `downloader.write` 时 `ctx.downloader` 只读。
这样能防止误用，但不防恶意代码。文档要明确写出这一点。

### 6.3 其他

`api_router` 挂载的路由**强制**经过现有鉴权依赖，插件无法注册匿名端点。

## 7. 开发者体验

- **SDK 文档**：`docs/dev/plugins/`，包括概念、每个扩展点的参考、事件列表、配置表单约定。
- **模板仓库**：`autobangumi-plugin-template`（cookiecutter），内含 `pyproject`、清单、示例 hook、pytest 契约测试、打包与签名提交流程。
- **CLI**：`uv run ab-plugin new | validate | pack | dev`。
  - `validate` 校验清单与 SDK 版本。
  - `dev` 把当前目录软链到 `config/plugins/local/` 并开启热重载。
- **契约测试**：`ab_sdk.testing` 为每类 Provider 提供参数化测试套件，例如 `DownloaderContract`、`RenameStrategyContract`。内置插件也必须通过。
- **示例插件**（随 4.0 发布）：`template-rename`、`include-filter`、`hardlink-organizer`、`jellyfin-refresh`、`webhook-on-event`、`custom-rss-site`。

## 8. 死代码与旧逻辑清理

以下由 `vulture` + 全仓引用核对得出（生产代码 0 引用）。
已剔除误报：FastAPI 路由、`@model_validator` / `@field_validator`、中间件 `dispatch`。
标「仅测试」的项目要连同对应测试一起删。

### 8.1 确认可删（生产 0 引用）

| 位置 | 项 | 备注 |
|---|---|---|
| `ab_decorator/__init__.py:47` | `api_failed` | |
| `network/site/mikan.py:25` | `mikan_title` | |
| `network/request_contents.py:62` | `post_form_json` | |
| `downloader/path.py:120,125,142` | `gen_movie_save_path`、`movie_rule_name`、`join_path` | |
| `downloader/client/qb_downloader.py:274` | `check_rss` | |
| `manager/renamer.py:71` | `print_result` | |
| `manager/renamer.py:327` | `rename_movie_file` | 电影重命名走 `rename_collection`，此函数无调用方 |
| `rss/engine.py:424` | `download_movie` | |
| `database/bangumi.py` | `update_rss`、`update_poster`、`not_added`（`:527/538/686`） | |
| `database/movie.py:171` | `not_added` | |
| `database/torrent.py` | `update_one_user`（`:36`） | |
| `database/passkey.py:45` | `get_passkey_by_id` | |
| `database/user.py:104` | `set_enabled` | 确认用户管理 API 不需要后删除 |
| `database/rename_operation.py:323` | `release_replacement_lease` | 状态迁移方法（`:300` 一带）提交时已清空 `lease_owner`，租约本身也会过期，大概率冗余；删除前核对 `renamer.py:799`、`:1103` 两处 claim 之后是否有提前 return 的路径 |
| `models/api.py` | `RssLink`、`AddRule`、`ChangeConfig`、`ChangeRule` | 整个文件可能可删 |
| `models/bangumi.py:144` | `SeasonInfo` | |
| `models/user.py:72` | `TokenData` | JWT 时代遗留 |
| `security/api.py:182,192` | `get_token_data`、`update_user_info` | |
| `parser/analyser/raw_parser.py:19` | `_detect_non_episodic_type` | |
| `parser/analyser/tmdb_parser.py:178` | `get_aired_episode_count` | |
| `parser/analyser/tokenizer/classic.py:896` | `_mostly_metadata` | |
| `parser/analyser/tokenizer/candidate.py:178`、`resolver.py:33` | `is_empty`、`selected_candidate_ids` | |
| `update/rss.py` | `update_main_rss`（整个文件） | |
| `update/data_migration.py:24` | `database_migration` | |
| `conf/const.py:152-160` | 未用 ANSI 颜色常量 | |

### 8.2 仅测试引用（删除或移入测试辅助）

`offset_scanner.check_single`、`aria2.set_renamed_path`、`bangumi.get_all_title_patterns`、`bangumi.match_poster`、`torrent.search_by_url`、`torrent.update_qb_hash`、`rename_operation.list_retryable`、`renamer.rename_file`、`searcher._fetch_tmdb_poster`、`security/jwt.create_access_token`。

`jwt.py` 整体随旧 JWT 兼容一起移除，见 8.3。

### 8.3 3.x 兼容层（4.0 断代移除）

4.0 **只支持从 3.3.x 升级**。更早的版本需先升到 3.3.x。启动时检测 `config/version.info`，低于 3.3 就拒绝启动并给出提示。

| 兼容层 | 位置 | 处理 |
|---|---|---|
| 3.0→3.1、3.1→3.2 跨版本迁移 | `update/cross_version.py`（`from_30_to_31`、`from_31_to_32`），`core/context.py:214-226` | 删除 |
| 旧 `data.json` 迁移 | `update/data_migration.py`、`LEGACY_DATA_PATH` | 删除 |
| `Database.migrate()` 删表重建 | `database/combine.py:103` | 删除（只剩上面的调用方） |
| 旧版明文 bearer token 导入 | `update/auth.py`、`database/auth.py:29` | 3.3 已导入，删除 |
| 旧 JWT cookie 兑换 | `security/jwt.py` 及相关 | 兼容期已过，删除 |
| GET 版控制端点（3.2 兼容） | `api/program.py:113-128`（注释已写「下个大版本移除」） | 删除 |
| `GET /auth/refresh_token` | `api/auth.py:94` | 删除 |
| `experimental_openai` 配置段 | `models/config.py:327,424`，`title_parser.py:114` | 配置迁移器转为 `llm` 段后删除 |
| 通知单 provider 旧字段 | `models/config.py:216-246`，`bark.py:22` token，`wecom.py:20` chat_id | 迁移到插件实例配置后删除 |
| `rename_method = "normal"` | `renamer.py:152` | 删除，配置迁移为 `none` |
| `season_offset` 无用参数 | `renamer.py:119` | 删除 |
| 旧 offset 建议模型 | `api/bangumi.py:23` | 核对前端后删除 |
| `Bangumi` 旧 movie 标志 | `models/bangumi.py:137` | 统一为 typed classifier，做 DB 迁移 |
| 「旧版下载器返回 bool」兼容 | `download_client.py:337-349` | Protocol 统一返回 `AddResult` 后删除 |
| tokenizer → `Episode` 投影 | `tokenizer/compat.py`、`raw_parser.py`、`title_parser._project_classic_release` | 流水线改用 `ParsedRelease` 后删除；`Episode` 仅保留为 LLM 输出 schema |
| `llm_plugins/` 独立安装器 | 整个目录 | 并入 `module/plugin/` |
| `LLMParser` 向后兼容属性代理 | `parser/analyser/llm.py` | 删除，同步更新测试 patch 路径 |
| qB < 4.x API 回退 | `qb_downloader.py:551` modern/legacy 双路径 | 定最低 qB 版本（建议 4.5）后评估 |

### 8.4 清理纪律

- 清理放在**独立 PR**，先于功能重构合入（阶段 0）。这样 diff 可审，回归可二分。
- 每删一项，跑 `uv run pytest` 和 `pnpm test:build`。前端同步删除对应 API 调用（`webui/src/api/`）。
- 在 CI 中加入 `vulture --min-confidence 80` 白名单检查，防止死代码回流。

## 9. 配置与数据迁移（3.3 → 4.0）

在 `module/update/v4.py` 中实现一次性迁移，迁移前把原配置备份为 `config.json.v3.bak`：

| 3.x | 4.0 |
|---|---|
| `downloader.type` + 连接字段 | 下载器实例 `default`（`plugins.instances`），`slots.downloader = "default"`；存量 `bangumi` / `torrent` 的 `downloader_id` 置为 `default` |
| `rss_parser.engine` + `llm.mode` | `plugins.slots.title_parser` 链 |
| `rss_parser.filter` | `exclude-regex` 插件默认选项 |
| `bangumi_manage.rename_method` | `plugins.slots.rename_strategy` |
| `revision_conflict_policy` | `plugins.slots.conflict_policy` |
| `notification.providers[]` | 通知插件实例 |
| `search_provider.json` | `generic-search` 插件选项 |
| `RSSItem.parser` 列 | `rssitem.source` + `metadata` 两列（DB migration） |
| `config/plugins/<llm-id>/` | 路径不变，清单从 `plugin.json` 转为 `plugin.toml` |

数据库新增 `plugin_kv` 表，`bangumi.plugin_options`、`bangumi.downloader_id`、`movie.downloader_id`、`rssitem.downloader_id`、`torrent.downloader_id` 列，并对 `rssitem` 拆列。
按 CLAUDE.md 的方式追加 `Migration` 条目。

## 10. 分阶段计划

每阶段都可独立合入 `4.0-dev`，主干保持可运行、测试全绿。

| 阶段 | 内容 | 产出 / 验收 |
|---|---|---|
| **P0 清理** | 第 8 节：死代码、3.x 兼容层；`renamer.py` 先做纯搬移式拆分（不改行为） | 生产代码行数减少；vulture CI；测试全绿 |
| **P1 插件运行时 + SDK 骨架** | `ab_sdk` 包（含 `ab_sdk.testing`）、`module/plugin/`（清单、加载、注册表、runner、熔断、EventBus、插件 KV）、`plugins` 配置段、`GET /api/v1/plugins`；SDK 边界测试 | 本地插件可加载、配置、随配置变更重载；已完成。签名目录来源与 LLM 安装器泛化、`dev_mode` 文件监听移到 P2 |
| **P2 迁移已有注册表** | 下载器、通知、LLM、搜索站点、定时任务改为扩展点，内置实现以 `core` 登记；`/api/v1/plugins`（列表、启停、配置、Provider 列表）与 WebUI 插件卡片（JSON Schema 表单）；`secret_field` 掩码；插件开发文档 | 已完成；内置行为不变（全量测试）。调整见第 0 节 |
| **P2.5 多下载器** | 下载器多实例；`downloader_id` 列与迁移；按实例路由 add / rename / delete；organize 逐实例扫描 | qb + aria2 并存的 e2e 用例；单实例行为不变 |
| **P3 流水线插件化：ingest** | `feed_source`、`title_parser` 链、`admission_policy`、`matcher`、`torrent.filter`、`ranker`、`metadata_provider` 链、`save_path`、`torrent.adding` | 新增 include / size 过滤；私有站 headers |
| **P4 流水线插件化：organize** | `media_files`、`file_parser`、`rename_strategy`（含 `template`）、`conflict_policy`、`file.renamed` 等事件 | 模板重命名；硬链接示例插件 |
| **P5 事件与外部接口** | SSE 改订阅 bus；`api_router`、`mcp_tool` 扩展点；`message_template` | 删掉 SSE 轮询；插件 MCP 工具 |
| **P6 前端插件** | Web Component 挂载点、`AbHost` 桥接、错误边界、`/plugins/<id>/web` 静态资源、`@autobangumi/plugin-ui` 包 | 示例插件「手动选种」以详情页标签形式可用 |
| **P7 生态** | 插件管理页（安装、启停、日志、错误）、签名目录发布流程、模板仓库（含前端模板）、`ab-plugin` CLI、文档（中 / 英 / 日） | 6 个以上示例插件上架 |
| **P8 发布** | beta 测试、性能对比（RSS 刷新耗时、内存）、升级指南、`docs/changelog/4.0.md` | `4.0.0-beta.1` → `4.0.0` |

阶段依赖：P0 → P1 → P2 → (P2.5 ∥ P3 ∥ P4) → P5 → (P6 ∥ P7) → P8。P2.5、P3、P4 可并行，P6 依赖 P5 的 `api_router` 与事件总线。

## 11. 风险与待决问题

已决议题（SDK 版本、插件依赖、前端插件、多下载器）见第 0 节。剩余风险：

1. **性能**。每个种子都要经过多段 hook，RSS 一次可能有几百条。Filter hook 需要支持批量接口 `accept_many`，并加基准测试。
2. **`release_replacement_lease` 无调用方**。初步判断冗余：状态迁移会清租约，租约也有过期时间。P0 删除前，确认 claim 之后的提前退出路径只靠过期回收是否可以接受（最长占用一个租约周期）。
3. **翻译**。事件 `describe()` 当前硬编码中文。插件化后要走 i18n key，否则第三方插件消息无法翻译。前端组件通过 `host.i18n` 拿当前语言。
4. **多下载器的跨实例一致性**。同一番剧中途更换下载器时，已下载种子仍留在旧实例。renamer 按 `torrent.downloader_id` 路由即可，但 UI 要明确展示每个种子所在实例。此外不做跨实例迁移。
5. **前端插件的 0.x 期 API 变动**。`AbHost` 与挂载点同样遵循 SDK 0.x → 1.0 的节奏，4.0 期间可能调整，文档要标注。
6. **vendor 依赖冲突**。两个插件 vendor 同一个包的不同版本时，私有前缀隔离能避免冲突。但包内的绝对 import 可能需要重写，需要在 P2 验证可行性。若不可行，退回为「vendor 包加入全局 path，同名包先到先得并告警」。
