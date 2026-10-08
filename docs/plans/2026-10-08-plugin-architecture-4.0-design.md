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

### 实施中的调整（P3）

- **ingest 不拆成独立的 `pipeline/ingest.py`**。钩子与 Provider 直接接入现有 `rss/engine.py`、`parser/title_parser.py`、`downloader/download_client.py`、`network/request_url.py`、`rss/analyser.py`，宿主逻辑原样保留，只在原位置调用扩展点。模块级代码通过 `module.plugin.host.get_runner()` / `hook_runner(point)` 拿到 runner（由 `AppContext` 构建时设置）；未设置 runner 或扩展点上没有钩子时直接走原路径，不构造快照。
- **钩子参数是冻结快照，不是 ORM 对象**。`ab_sdk.ingest` 定义 `TorrentInfo`、`BangumiInfo`、`AddRequest`、`HttpRequest`、`Metadata` / `MetadataRequest`；解析结果直接传冻结的 `ParsedRelease`，SDK 只给出只读 Protocol `Release`。transform 钩子返回类型不符时按失败处理并计入熔断（`HookRunner.transform(expect=...)`）。
- **`torrent.filter`** 在规则自带的排除过滤之后执行，排除过滤仍是宿主逻辑，语义不变。被拒的种子与排除过滤一样不关联番剧。手动「收集」整季（`download_bangumi`）同样经过该钩子。
- **`title.parsed`** 只接在 `TitleParser.raw_parser`（新规则创建、收集）的准入判定前。偏好去重 `_select_preference_skips` 使用的同步解析不经过钩子。
- **`torrent.adding`** 允许修改 `save_path`、`category`、`tags`。宿主保证 `ab:<id>` 标签存在（被删时补回）。暂停状态暂不开放，因为 `add_torrents` 契约没有对应参数。
- **`http.request`** 只作用于 `RequestURL.get_url`（RSS、种子文件、站点页面），只能改请求头；POST（通知）不经过。
- **`metadata_provider` 暂不做链式**，仍由 `RSSItem.parser` 选择单个 Provider，列不迁移。内置 mikan / tmdb 以 `core` 登记，行为与 3.x 完全一致，包括 TMDB 未命中时清空年份与海报、mikan 非 `AttributeError` 异常照旧上抛。Provider 返回完整的新 `Metadata`，而不是增量 patch，这样「置空」也能表达。
- **内置插件 `ingest-filters`**（`module/plugins/builtin/ingest-filters/`）只实现全局「包含过滤」，默认启用、留空不生效。种子大小目前不在 RSS 解析结果中（`Torrent` 无 size 列），`size-limit` 推迟到 `feed_source` 解析 enclosure length 之后；按订阅覆盖需要 `Bangumi.plugin_options` 列，同样推迟。
- **推迟**：`feed_source`（与 `FeedConfig.source` 替代 `RSSItem.parser` 一起设计）、`title_parser` 链、`admission_policy`、`bangumi_matcher`、`release_ranker`、`rule.created`、`save_path` Provider，以及第 11 节的批量 `accept_many`。
- `module/plugin/context.py` 改为延迟 import `module.database`，否则网络层引用 `module.plugin.host` 会形成循环依赖。

### 实施中的调整（P5）

- **系统事件类移入 `ab_sdk.events`**，`SystemEvent` 由封闭 Union 改为基类（插件也可定义可通知事件）；`module.notification.events` 只做再导出。`kind` 沿用 3.x 取值（`rss_failure` 等，通知中心按它存储与翻译），不改成 `rss.failure` 式的点分名。
- **通知管理器仍是事件入口**：第 4.2 节设想的「通知管理器、inbox 都作为总线订阅者」未实施。`NotificationManager.send_event` 依次写通知中心、发布到总线、推送外部渠道，调用方与外部行为不变；改成纯总线驱动要等 P3/P4 的流水线事件稳定后再统一。
- **SSE 只有 `notification` 改为订阅总线**（`inbox.changed`，通知中心写入 / 已读 / 删除时发布，立即推送）。status / downloader / log / update 是状态快照而非事件，仍按节拍采样；`inbox_revision` 计数保留，作为帧里的 `revision` 字段。
- **插件路由用分发路由实现**：FastAPI 不能卸载路由，宿主只注册 `/api/v1/plugins/{plugin_id}/{path:path}`（鉴权依赖在此强制），按插件 id 转发给由插件 `APIRouter` 合并成的 ASGI 应用，插件变更时重建。插件路由不进 OpenAPI。
- **按插件作用域的 Provider id**：`ExtensionPoint` 新增 `scoped`，`api_router` / `mcp_tool` / `mcp_resource` 的 id 只需在插件内唯一（注册表键为 `<plugin_id>/<id>`）。MCP 工具名用 `<plugin-id>__<id>` 而非 `.`，因为 Anthropic / OpenAI 等 LLM API 的工具名只接受 `^[a-zA-Z0-9_-]{1,64}$`。
- **`message_template` 只作用于系统事件的外部推送**，钩子签名 `(RenderedMessage, event, channel)`，按渠道各调用一次；「新集数」通知仍用渠道里的单集模板（`_format_message` 是同步接口，改造留到通知渠道迁到 `config_model` 时）。
- **i18n（第 11 节风险 3）先给出 key**：`SystemEvent.i18n()` 返回 `notifications.kind.<kind>` 与 `payload()`，与前端现有文案键一致；外部推送与通知中心的中文兜底文案不变。插件事件的前端翻译依赖 P6 的 `host.i18n`。
- 进程级访问器 `module.plugin.host.get_bus/set_bus`、`get_runner/set_runner`、`publish()`，由 `AppContext` 构造时设置，未设置时为空操作。MCP 的 `tools/list_changed` 通知未实现（客户端重新 list 即可看到插件工具变化）。

### 实施中的调整（P4）

拆分与扩展点：

- **`renamer.py` 拆分**：revision 替换事务（普通改名日志、V1→V2 替换、恢复、操作状态、版本占用者）搬到 `manager/revision_saga.py` 的 `RevisionSaga`，`Renamer` 以 mixin 方式继承它（`class Renamer(RevisionSaga)`），而不是构造函数注入。这样第一个提交是纯搬移，测试仍能访问 `renamer._run_ordinary_rename`、`renamer.events`、`renamer._downloader_type`。`renamer.py` 从 1805 行降到 1061 行（含 P4 新增的扩展点接入）。
- **重命名方式**：宿主只以 `core` 登记 `none`（`manager/rename_strategies.py` 的 `NoRename`）。`pn`、`advance`、`template` 由内置插件 `rename`（`module/plugins/builtin/rename/`，默认启用）提供。设置值 `bangumi_manage.rename_method` 直接作为 Provider id，`slots` 与迁移器留到 P2.5。id 未登记（插件停用或被熔断）时记录一次日志并按 `none` 处理。
- **纯搬移的一处例外**：3.3 中未知重命名方式遇到电影文件时会改名为 `{title}{suffix}`；现在未知 id 一律按 `none` 处理，保留原名。
- **`normal`**：`gen_path` 中已没有 `normal` 分支。`conf/config.py` 中 `normal → none` 的转换属于 3.x 兼容层（第 8.3 节），保留不动。
- **字幕**：删除 `subtitle_pn` / `subtitle_advance`，类别由 `RenameInput.kind` 给出。因此 `test_renamer.py` 有 5 处调用参数从 `subtitle_*` 改为 `pn` / `advance`（断言未改），`test_plugin_extensions.py::test_providers` 的期望值增加 `rename_strategy: []`。既有测试依赖进程注册表中的 `pn` / `advance`，由 `conftest.py` 的 autouse fixture 登记内置插件 `rename`，与生产默认一致。除此之外，pn / advance / none 的输出与 3.3 逐字节一致。
- **策略调用是同步的**：`HookRunner.call_provider_sync` 在熔断器内调用策略并校验返回值（非空字符串），没有超时；Jinja2 渲染也没有超时，只受沙箱 `MAX_RANGE` 限制。`RenameSkipped` 不计入熔断；其它异常与非法返回值计入熔断，并同样按跳过处理。
- **跳过通知**：新增系统事件 `rename_skipped`（`RenameSkippedEvent`，WebUI 的 `KNOWN_KINDS`、i18n 与跳转路由同步增加），不复用 `rename_conflict`。同一 (种子 hash, 原因) 每个进程只通知一次。字幕被跳过同样会阻止打 `ab:renamed` 标签，用户修正后种子会被重试。
- **模板失效的后果**：已保存的模板若不再通过校验（手工改配置、Jinja2 升级），整个 `rename` 插件加载失败，`pn` / `advance` 随之消失，所有种子按 `none` 处理。插件因连续 5 次异常或非法返回值被熔断时同样如此。
- **`media_files` 与 `conflict_policy`** 只解析固定的 core id `default`（`ab_sdk.rename.CORE_ID`）。插件可以登记实现，但选择要等 P2.5 的 `slots`。`conflict_policy` 的接口改为 `decide(ConflictRequest) -> ConflictDecision`：`ConflictRequest` 带上宿主读取的设置值 `configured`（`bangumi_manage.revision_conflict_policy`，测试 patch 的是 `module.manager.renamer.settings`，所以设置仍在 `renamer.py` 中读取）和宿主计算的 `strict_upgrade`。宿主仍只在「唯一占用者、双方都是单文件种子、双方身份完整」时执行替换。
- **事件字段**：`FileRenamed` 的类别字段叫 `file_kind`，因为 `kind` 是 `Event` 的类变量；`OrganizedFile` 保留 `kind`。路径为下载器视角、以 `/` 拼接的绝对路径；`downloader_id` 在 P2.5 之前固定为 `"default"`。
- **`TorrentOrganized` 的投递是至少一次**：进程内按 hash 记忆已发布的最终文件集合，重启后、或文件集合变化时会再次发布。重命名方式为 `none` 的种子同样发布。订阅者必须幂等。
- **WebUI**：重命名方式下拉框经 `usePluginProviders` 合并插件提供的 id（如 `template`），`rename_method` 类型放宽为字符串。`template` 在 设置 → 番剧管理设置 → 重命名方式 中选择，模板在 设置 → 插件 → 重命名 中填写。
- `ab_sdk` 新增 `ab_sdk.rename`（契约与冻结快照 `RenameInput`、`Revision`、`RevisionTask`、`ConflictRequest`，以及 `pad()`），`SDK_VERSION` 升到 `0.4.0`。

插件运行时（为内置插件 `hardlink` 补齐）：

- **清单字段 `default_enabled`**（默认 `true`，只对内置插件生效）。`hardlink` 设为 `false`，内置但默认停用。
- **`@subscribe(kind, timeout=...)`**：覆盖总线默认 30 秒的单个事件处理超时。跨盘复制一集常超过 30 秒，超时会计入熔断，5 个种子后插件就会被停用。`hardlink` 用 3600 秒，文件操作放在 `asyncio.to_thread` 中执行，不阻塞事件循环。
- **插件的可通知事件进入通知中心**：P5 中插件发布的 `SystemEvent` 只进事件总线。现在 `PluginBus.publish` 把它交给 `NotificationManager.send_event`，与宿主事件一样写入通知中心、发布到总线、推送外部渠道。前端没有对应翻译的 kind 显示 `describe()` 的中文标题与正文。

内置插件 `hardlink`（`module/plugins/builtin/hardlink/`）：

- 插件 id 为 `hardlink`，不是第 4.4 / 7 节示例中的 `hardlink-organizer`。它订阅 `torrent.organized` 而不是第 2.3 节草图中的 `file.renamed`：前者给出种子的完整最终文件集合，重命名方式为 `none` 时也会发布。
- `source_root`、`library_root` 为必填的绝对路径，`library_root` 不能位于 `source_root` 内。插件代码加载过一次后才有设置表单，所以首次启用必然加载失败（缺少必填项），用户随后在出现的表单中填写、保存，插件重新加载。
- `path_map` 是对象列表，P2 的 JSON Schema 表单不支持对象数组（显示为「不支持的字段」），P4 期间只能在 `config.json` 中填写。表单支持对象数组留到 P6 / P7。
- 所有放置（新建与版本升级替换）都先写到同目录的临时文件 `.<文件名>.<随机串>.ab-hardlink`，再 `os.replace` 到目标；失败时删除临时文件。复制中断不会在目标留下半个文件，否则重试时它会被当成「不是本插件创建的」冲突。临时文件名每次不同，因为补链与订阅可能同时处理同一个目标。
- `hardlink.failed` 的通知正文只能显示种子 hash，因为 `TorrentOrganized` 不带种子名；补充种子名留到 P2.5 / P6。
- 「由插件创建」记录在插件 KV 中：键 `link:<目标路径>`，值为 `[源文件身份, 目标身份]`，身份为 `lstat` 的 `[st_dev, st_ino, st_size, st_mtime_ns]`。加入大小与修改时间，是因为旧文件删除后 inode 可能被复用。目标是源的硬链接、软链接或大小与修改时间相同的副本，或两个身份都与记录一致时，视为已完成并补写记录：放置后、写记录前协程被取消或进程退出，留下的文件不会被当成冲突。版本升级只替换目标身份与记录一致的文件，用户在原位置放的文件不会被覆盖。
- 目标被占用、跨文件系统按 `skip` 跳过、源不在 `source_root` 下等问题，每个种子合并成一条 `hardlink.failed` 通知，`dedup_key` 为种子 hash。由于至少一次投递，长期存在的冲突在每次重启后会更新同一条通知。
- 补链 `backfill()` 以插件路由 `POST /api/v1/plugins/hardlink/backfill` 提供，只在用户调用时运行，返回 `linked` / `exists` / `conflict` / `failed` 计数，不发通知。它遍历本地 `source_root`，不经过 `path_map`。插件不能 import `module.*`，所以按固定扩展名（`.mp4` / `.mkv` / `.ass` / `.srt`，与 `media_files` 的 core 实现相同）挑选文件。
- **补链按钮推迟到 P6**：设置页的按钮依赖 P6 的 `settings.section` 挂载点，P4 只提供 REST 路由。
- 删除种子不会删除媒体库中的链接。

未实施（推迟）：

- 第 10 节 P4 行中的 `file_parser` 扩展点。
- 第 7 节的 `ab_sdk.testing.RenameStrategyContract` 契约测试套件（P7 已补）。

两份 P4 实现与移植：

- P4 有两份独立实现。另一个会话的版本（提交 a0706513、12e7e2f5，基于旧 P5 0b6de315）曾推到 `refactor/4.0-p4-organize`，现保留为 `refactor/4.0-p4-organize-cloud`（head 544628f6）。本分支保留本节上文的设计，因为它符合已确认的决策：`pn` / `advance` / `template` 都在内置插件 `rename` 中，坏模板跳过文件并通知、不退回 `pn`，另有 `hardlink`。另一份的 `rename-template` 插件、`BangumiLink`、`ab_sdk.organize` 与由 `PluginManager` 设置进程级总线的做法没有移植。
- 从另一份移植并按本分支改写的内容：
  - **内置插件 `media-server-refresh`**：订阅 `torrent.organized`（另一份订阅 `file.renamed`；前者在重命名方式为 `none` 时也会发布），等待 `delay` 秒，把期间的事件合并成一次 Jellyfin / Emby / Plex 刷新请求。未填写地址或 API Key 时不做任何事，所以与另一份相同，默认启用。由于至少一次投递，已配置时每次重启最多多出一次合并后的刷新。
  - **死代码**：删除 `Renamer.rename_file` / `_rename_media_file`、`_lookup_offsets` / `_normalize_path`、`BangumiDatabase.match_by_save_path`、`TorrentDatabase.search_by_qb_hash`、`RenameOperationDatabase.release_replacement_lease`。删除前确认它们在本分支（含 `revision_saga.py`）没有生产调用方。原测试改为经 `rename()` 与 `_batch_lookup_offsets` 驱动。`season_offset` 从 `gen_path` 起整条重命名链路移除，`_batch_lookup_offsets` 的结果从 `(集数偏移, 季度偏移, 类型)` 改为 `(集数偏移, 类型)`：季度偏移已体现在 Season 文件夹，文件名从未使用它。
  - **插件配置 422**：`field_validator` 抛出的 `ValueError` 会留在 `ValidationError.errors()` 的 `ctx` 中，无法 JSON 序列化，保存配置返回 500（`hardlink` 的路径校验、`rename` 的模板校验都会触发）。现在以 `include_context=False` 返回 422。
  - **用户文档**：`docs/{,en/,ja/}config/manager.md` 增加 `template`、`hardlink`（含 `path_map` 与 Docker 下硬链接不能跨文件系统的说明）与 `media-server-refresh` 三节，按本分支的设计重写；`CHANGELOG.md` 增加 P4 条目。
- 移植时发现并修复：vulture 白名单缺少 `rename` / `hardlink` 内置插件的入口（CI 的 vulture 检查会失败）；VitePress 不给行内代码加 `v-pre`，文档里行内代码中的 Jinja2 示例在构建时报 `_ctx.pad is not a function`，现在用 `::: v-pre` 容器包住（含本设计文档第 3.6 节与插件开发文档）。

### 实施中的调整（P2.5）

配置模型（第 4.4 节）：

- **`downloader` 配置节移出运行时模型**。下载器是 `plugins.instances` 中的 `PluginInstance`（`id`、`point`、`provider`、`options`），第 4.4 节草图中的 `plugin` 字段改为 `point` + `provider`，`default?` 标记改为由 `slots.downloader` 指定默认实例。新配置默认带一个 qB 实例 `default`，默认值与 3.3 相同。
- **`plugins.slots` 是带默认值的类型化模型**（`downloader="default"`、`rename_strategy="pn"`、`conflict_policy="hold"`、`media_files="default"`），不是任意 `dict`，也不接受其它键。原因是 WebUI 需要固定的键来绑定，新安装也要有完整的值。`title_parser` / `metadata_provider` 链等到对应扩展点实施时再加。
- **`plugins` 段的校验**：实例 id 唯一；下载器实例的 `options` 按 `DownloaderOptions`（host / username / password / path / ssl，`$VAR` 展开规则不变）校验；`slots.downloader` 必须指向一个下载器实例。PATCH /config 的请求体不符合时返回 422。
- **`Config.downloader` 保留为只读属性**，返回 `slots.downloader` 所指实例的冻结视图 `DownloaderInstance`（`type` 即 `provider`）；`Config.downloader_instance(id)` 按 id 取实例。它不参与序列化，也不接受输入。第一部分的调用方（下载门面、`path.py`、checker、`revision_saga._downloader_type`、`AppContext`）因此不变，`_downloader_type` 的取值也不变（存量 `rename_operation` 行依赖它）。按实例路由在 P2.5 第二部分。
- **秘密字段**：`DownloaderOptions.password` 带 `secret` 标记（与 `secret_field()` 相同；直接写 `Field`，因为 mypy 的 pydantic 插件看不到经 `**kwargs` 传入的别名）。GET / PATCH /config 没有另加按 schema 的实例掩码：现有的按键名掩码已覆盖 `password`，列表项的掩码还原按身份匹配，身份包含实例 `id`。对下载器来说按 schema 掩码的结果完全相同。插件下载器有了自己的 options schema 后再加。

slots 解析：

- `rename_strategy` 读 `slots.rename_strategy`，未登记时仍记录一次日志并按 `none` 处理。`media_files` 读 `slots.media_files`，未登记时退回 `default`。`conflict_policy` 读 `slots.conflict_policy`，未登记时退回 `hold`，不会误删旧版本。后两者不记日志，因为每个文件都会解析一次。
- **冲突策略改为两个 Provider**：第 9 节把 `revision_conflict_policy` 迁到 `slots.conflict_policy`，slot 的值就是 Provider id。因此宿主以 `core` 登记 `hold` 与 `replace` 两个 `CoreConflictPolicy`，不再登记 `default`；`ConflictRequest` 删除 P4 加入的 `configured` 字段。`ab_sdk` 升至 0.5.0。`GET /api/v1/plugins/providers` 仍不列出 `conflict_policy` / `media_files` 的插件候选。

迁移器（第 9 节，`module/update/v4.py`）：

- 按源字段是否存在触发：`downloader`、`bangumi_manage.rename_method`、`bangumi_manage.revision_conflict_policy`。字段是「移动」而不是复制，第二次运行看不到源字段，什么也不做，也不会用 4.0 格式的文件覆盖 `.v3.bak`。下载器字段合并到已有的 `default` 实例上，没有时新建。
- `normal → none` 并入 `rename_method → slots.rename_strategy` 的迁移，`Settings._migrate_old_config` 中的对应分支随之删除（第 8.3 节）。掩码哨兵清洗保留在 `_migrate_old_config`。
- 只有需要迁移时才备份。新文件先写到 `<文件名>.tmp` 再 `os.replace`。迁移后的字典先用 `Config.model_validate` 校验；任何失败都从备份恢复原文件，记录 `critical` 日志并抛出 `ConfigMigrationError`。日志与异常消息写明出错字段（取 pydantic 错误的 `loc`），因为此时 `setup_logger` 还没有运行。配置文件本身不是合法 JSON 时由 `json` 直接报错，与之前相同。
- **接线**：迁移器在 `Settings.__init__` 中、`load()` / `save()` 之前调用，所以 `import module.conf` 失败即拒绝启动。`module/update/__init__.py` 原先在包初始化时 import 依赖 `module.conf` 的子模块，`module.conf` 无法 import `module.update.v4`。现在包初始化不 import 任何子模块，6 处调用方改为直接 import 子模块。没有用模块级 `__getattr__` 懒加载，因为 mypy 会把这些名字推断为 `Any`。
- **版本闸门不动**，仍在 `AppContext.startup` 中。P0 发现的「`Settings()` 在版本闸门之前改写 config.json」由备份解决：低于 3.3 的配置仍会先被迁移、再被闸门拒绝，原文件保存在 `config.json.v3.bak`，退回 3.3 时要用它恢复。`Settings` 加载后仍立即保存一次，与之前相同。
- **环境变量**：`ENV_TO_ATTR` 不变，仍按 3.3 的位置写入（`AB_DOWNLOADER_*` / `AB_DOWNLOAD_PATH` → `downloader`，`AB_METHOD` / `AB_REVISION_CONFLICT_POLICY` → `bangumi_manage`），再由同一个 `migrate_v3_dict` 移到默认实例与 slots。设置向导（`/setup/complete`）把下载器写入 `slots.downloader` 所指的实例。

数据库与 WebUI：

- 迁移 v26 为 `bangumi`、`movie`、`rssitem`、`torrent` 增加 `downloader_id`。每张表一个守卫：列已存在，或表不存在（之后由 `create_all` 按模型建表，自带该列）时跳过。取值见下文第二部分（规则、订阅与电影为空表示跟随默认实例，种子默认 `default`）。
- WebUI：「下载器设置」编辑 `slots.downloader` 所指的实例（`provider` 与 `options`），「番剧管理设置」中的重命名方式与版本冲突策略绑定到 `plugins.slots`。两个分区的未保存标记都以 `plugins` 配置段判断，所以修改其中一个，两个分区都会显示未保存。插件卡片保存后 `refreshGroup('plugins')` 会用服务端的值覆盖整个 `plugins` 段，包括尚未保存的下载器与 slots 修改（之前只影响插件 options）。
- 用户文档 `docs/{,en/,ja/}config/{downloader,manager}.md` 与插件开发文档改为新的配置位置。

第二部分（路由、整理与 WebUI）：

- **`DownloadClient(instance_id=None)`**，`None` 为默认实例。客户端缓存与凭据闩锁按实例 id 分开；引用计数本来按具体客户端对象计，不变。第 3.5 节的统一工厂 `create(config: PluginConfig)` 未实施：工厂仍接收 P2 契约的 `DownloaderConnection`，实例 `options` 目前就是 `DownloaderOptions` 的字段。
- **`DownloaderPool`**：一次操作（一轮 RSS、整季补全）内按实例 id 惰性进入 `DownloadClient`，退出时全部释放。进入失败的实例在这次操作内记住，之后直接抛 `ConnectionError`，不再重复登录。`RSSEngine.refresh_rss` 的参数由 `DownloadClient` 改为 `DownloaderPool`，测试改用 `test.factories.SingleClientPool`（27 处调用）。
- **实例选择**：`resolve_downloader_id(*候选)` 取第一个已配置的实例 id，都为空时用 `slots.downloader`。指向已删除实例的候选记 warning 后跳过，因此删除实例后，选择它的规则与订阅改用默认实例。新种子按 规则 → 订阅 → 默认 选择；由订阅新建的规则在解析时继承订阅的 `downloader_id`（`rss/analyser.py`）；手动收集与整季补全按 规则 → 默认。
- **规则、订阅与电影的 `downloader_id` 为空表示跟随默认实例**。第一部分的 v26 给这三张表 `DEFAULT 'default'`，这样「规则 → 订阅」的继承永远走不到订阅，用户改默认实例后存量规则也仍钉在 `default`，与第 3.5 节「为空时用默认实例」矛盾。v26 尚未发布，所以直接修改它：这三张表加列不带默认值（存量为 `NULL`），`torrent` 仍为 `DEFAULT 'default'`（存量种子都在 3.3 的下载器中）。已经运行过第一部分 v26 的开发库需要手动把这三列置空。`BangumiUpdate`、`MovieUpdate`、`RSSUpdate` 加入该字段，`POST /rss/add` 保存它。
- **种子行的 `downloader_id`** 由 `DownloadClient.add_torrent` 写入投递的实例；未匹配的孤儿种子保持 `default`。投递时实例不可用：种子不入库、下一轮重试，不发 `DownloadFailureEvent`（不可用由重命名轮次通知）。
- **重命名逐实例运行**：`manager/renamer.py` 的 `rename_all()` 供 `loops.rename_tick` 与 apply-offset 使用。进入失败（连不上、凭据被拒、Provider 未登记）的实例跳过，其它实例照常处理；`DownloaderUnavailableEvent` 只在「可用 → 不可用」时产生一次（进程内集合），恢复后再次不可用会再通知。`Renamer` 自身抛出的异常仍中断本轮，与之前相同。apply-offset 触发的重命名丢弃事件（之前也丢弃）；实例恰好在这一次变为不可用时，这次不可用不会通知。启动等待循环仍只检查默认实例。
- **`DownloaderUnavailableEvent`** 增加 `instance_id`（默认 `"default"`），`dedup_key` 由 `downloader:<host>` 改为 `downloader:<instance_id>`，payload 增加 `instance`。`ab_sdk` 仍为 0.5.0（本阶段未发布）。
- **版本替换事务按实例过滤**：`list_active_replacements(downloader_type)` 只返回本实例的事务。否则实例 A 的轮次在 A 上查不到 B 的新种子，会进入破坏性的 `_recover_missing_replacement`。`_downloader_type()` 改读 `self.client.instance`。
- **offset 查找**：同一 hash 有多条种子行时以本实例的行为准，其它实例的行作为后备。`path_to_bangumi` / `gen_save_path` 增加 `root`（实例的下载目录），重命名与新规则保存目录按实例计算。
- `FileRenamed` / `TorrentOrganized` 带真实的 `downloader_id`；`hardlink` 的 `path_map` 本来就按它取映射，无需改动。
- **规则换实例**：删除规则（删除文件）时按种子行记录的实例加上规则当前的实例逐个删除。更新规则时实例变了：旧种子不移动，原实例上的 qB RSS 规则不改，只按新实例的下载目录重算 `save_path`；实例不变且路径变化时才移动（路径不变时不再连接下载器）。
- **API**：`GET /downloader/torrents` 汇总所有实例、每条带 `downloader_id`，不可用实例跳过，全部不可用时返回 503（原先连接异常直接 500）。暂停 / 恢复 / 删除 / 打标请求带 `downloader_id`（空为默认实例），未知 id 返回 404；自动打标逐实例进行。新增 `GET /downloader/instances`（`id`、`provider` 与默认 id），供规则 / 订阅选择下载器。SSE 的 downloader 帧同样汇总，超时按实例计算。MCP `list_downloads` 汇总所有实例并带 `downloader` 字段，全部不可用时返回空列表（原先抛错）。
- **WebUI**：「下载器设置」列出所有实例（点击编辑、添加、删除、设为默认，默认实例不能删除；新 id 只接受字母、数字、`_`、`-`，这是前端限制）。规则编辑的高级选项与添加订阅新增下载器选择，留空为默认实例，只有一个实例时不显示；实例列表每次打开时请求，设置页增删实例后无需刷新。下载器页在多实例时加「下载器」列，规则 / 孤儿种子列表在已下载的种子上标出实例。批量操作仍按 hash 选择，按所在实例分组请求；同一 hash 同时在两个实例中时会作用于两个实例。
- **`refreshGroup` 只刷新给定字段**：插件卡片保存后只刷新 `plugins.enabled` / `options`，不再覆盖未保存的实例与 slots 修改（第一部分记录的问题）。「下载器设置」与「番剧管理设置」仍共用 `plugins` 未保存标记。

审阅修正（覆盖上文相应条目）：

- **保存目录随实例重新生成**：`save_path_for(data, root)`（`downloader/path.py`）在已存的 `save_path` 位于该实例下载目录之下时沿用它，否则按该实例的下载目录重新生成（比较用 `PureWindowsPath`，`\` 与 `/` 都认）。`add_torrent` 每次投递都经过它并写回规则，所以默认实例切换、规则的实例被删除、订阅指向别的实例时，新种子都进目标实例的目录。代价：单实例用户修改下载目录后，存量规则的新种子也进新目录（3.3 沿用旧目录）。只在「属于另一个已配置实例」时重算做不到「实例被删除」的情况，所以按「不在本实例目录之下」判断。
- **按实例匹配与移动**：`TorrentManager` 在每个实例上按两个目录匹配种子：已存的 `save_path`（与之前相同，单实例改过下载目录时仍能找到旧种子），以及 `save_path_for(规则, 该实例目录)`。更新规则且实例不变时，对种子行记录的每个实例（加上规则当前的实例）分别计算新目录并移动。qB RSS 规则只在有匹配种子的实例与规则自己的实例上改写，因为 `rss/setRule` 在别的 qB 上会新建一条启用的自动下载规则。这样「规则未指定实例、种子经订阅进了另一实例」时也会移动。规则自身的实例仍不带订阅后备，因为种子行已记录实际位置。
- **删除逐实例隔离**：一个实例不可用或删除失败时，其它实例照常删除，最后返回 500 并列出失败的实例。删除规则（删除文件）时先删各实例上的种子，全部成功才删种子行与番剧；有实例失败时两者都保留并返回 500，实例恢复后可重试（已删净的实例匹配不到种子，直接跳过）。种子行经外键引用番剧，所以不能只保留失败实例的种子行。不删文件时不连接下载器，与之前相同。
- **整季补全与自动打标跳过不可用实例**：`eps_complete` 跳过该规则（不标记 `eps_collect`，下一轮重试），其它规则照常补全并保存；`POST /downloader/torrents/tag/auto` 改用 `DownloaderPool`，不可用实例跳过。
- **版本替换事务的过滤只在多实例时生效**：只有一个下载器实例时 `list_active_replacements(None)` 返回全部事务，与 3.3 相同；否则改了主机地址（键里含主机哈希）后进行中的事务永远不会恢复。多实例下改主机地址仍有这个问题（见推迟项）。
- **迁移备份不覆盖已有备份**：`.v3.bak` 已存在时依次取 `.v3.bak.1`、`.v3.bak.2` …，失败恢复与日志都用本次写的备份。降级回 3.3 再升级时，第一份备份里的真实下载器凭据因此保留。

未实施（推迟）：

- 第 10 节验收中的 qb + aria2 并存 **Docker e2e** 未加。以进程内测试替代：两个 mock 实例并列（按规则 / 订阅投递、在另一实例重命名、一个实例不可用、规则换实例后删除），以及 qB 与 aria2 实例各自得到对应后端与不同的 `downloader_type`。Docker 版需要在 `e2e/compose/downloader.yml` 加入固定 digest 的 aria2 镜像。
- aria2 的 gid ↔ 番剧映射表（`database/aria2.py`）不区分实例；两个 aria2 实例的 gid 相同的概率很低，未处理。
- `GET /api/v1/plugins/providers` 仍不列出 `conflict_policy` / `media_files` 的插件候选；插件下载器的 options schema 与按 schema 掩码（见上文）。
- 多实例时修改某个实例的主机地址，该实例上进行中的版本替换事务找不到（`_downloader_type` 键含主机哈希）。可选做法：键改为 `<type>:<instance_id>` 并兼容旧键查询，或按「键不属于任何已配置实例」把孤儿事务交给同类型的唯一实例。

### 实施中的调整（P6 第一部分：后端与 `@autobangumi/plugin-ui` 包）

- **清单 `[[plugin.ui]]`** 由 `module/plugin/manifest.py` 的 `PluginUi` 校验：`slot` 取五个挂载点之一，`element` 须匹配 `^ab-plugin-[a-z0-9]+(-[a-z0-9]+)*$`，`entry` 须是 `web/` 下的相对路径（不含 `..`、反斜杠），`title` 至少一种语言。校验失败时整个清单被拒绝，与其它清单字段一致。
- **挂载点列表用新路由 `GET /api/v1/plugins/ui`**（不改 `GET /plugins` 的形状），只列已启用插件，按插件 id 排序。`PluginCandidate` 新增 `root`（目录插件与 pip 包在文件系统上时有值；zip 安装的 pip 包为 None，没有 `web/` 可提供）。
- **静态资源 `GET /api/v1/plugins/{id}/web/{path}`** 用 `FileResponse` 提供，只读已启用插件的 `web/` 目录；`resolve()` 后用 `is_relative_to` 判定，`..`、绝对路径、指向目录外的符号链接和未启用插件都返回 404。`.js` / `.mjs` 固定为 `text/javascript`（不依赖系统 `mimetypes`），带 `Cache-Control: no-cache`（插件升级后文件名不变，按 ETag 重新验证）。
- **鉴权沿用路由器级的 `get_current_user`**。WebUI 用 HttpOnly 会话 cookie（`token`，`SameSite=Strict`，路径 `/`）登录，同源的 `<script type="module">` 与 `import()` 会带上它，无需 header。此路由必须注册在 `plugin_routes_router` 的分发路由之前（`api/__init__.py` 已是这个顺序）；因此插件自己的 `api_router` 不能使用 `web/` 前缀。
- **CSP `script-src 'self'` 只加在 SPA 文档上**（`index.html`、`sw.js` 等 dist 根文件），不加在 API 与 `/docs`：Swagger 页面依赖内联脚本与 CDN。`main.py` 的 SPA 挂载抽成 `mount_webui(app, dist)` 以便测试。
- **`index.html` 的内联深色模式脚本移到 `public/theme-init.js`**，否则 CSP 会拦下它。在线更新若换入旧版 dist（仍带内联脚本），只会失去首屏深色模式的预先应用（页面载入后 `useDarkMode` 仍会设置），不影响功能。构建产物 `dist/index.html` 经 headless Chrome 验证：登录页在该 CSP 下正常渲染。
- **Vite 只给 `preview` 加 CSP，不给 dev**：dev 服务器与 `vite-plugin-pwa` 的开发态都会注入内联模块脚本，加了会拦下它们。
- **`@autobangumi/plugin-ui` 是 pnpm 工作区包**（`webui/pnpm-workspace.yaml`，`private`，不发布），WebUI 以 `workspace:*` 作为 devDependency。内容：`src/index.ts`（`AbHost`、`PluginUiSlot`、各挂载点的 `AbSlotContext`、`AbPluginElement`）、`tokens.css`（`--ab-*` 变量，取值回落到宿主的 `--color-*` 等设计令牌，深浅色随宿主切换）、`template/`（Vite 库模式：单文件自包含 ES module，输出到 `../web/index.js`，把 `tokens.css` 以 `?inline` 放进 Shadow DOM）。宿主侧的挂载、`AbHost` 实现与错误边界在第二部分。
- **`AbHost.api` 的范围**：不以 `/` 开头的路径相对 `/api/v1/plugins/<id>/`；以 `/api/v1/` 开头的宿主 API 只允许 GET（第 3.8 节的「公开只读 API」）。接口形状为暂定，4.0 期间可能调整。

### 实施中的调整（P6 第二部分：WebUI 宿主与示例插件）

- **`PluginSlot`（`components/plugin-slot.vue`）** 是五个挂载点共用的宿主组件：导入模块（`services/plugin-loader.ts`，同一 URL 只导入一次，失败不缓存）、确认 custom element 已定义、创建元素，先设置 `host` 与 `context`，再插入宿主自己创建的 Shadow DOM 包裹层。包裹层隔离宿主的全局样式，并在其中注入 `tokens.css`，所以不构建的插件（如内置 `hardlink`）直接用 `--ab-*` 变量即可；用 Vite 模板构建的插件仍在自己的 Shadow DOM 里再引一份，值相同。`context` 变化时重建元素，组件不必自己监听。
- **`AbHost` 的实现**（`services/plugin-host.ts`，依赖由 `hooks/usePluginHostDeps.ts` 注入，测试用替身）：路径用 `new URL()` 解析后再判定，`..`、`%2e%2e`、`//host`、完整 URL 都按越界处理；不以 `/` 开头的路径相对 `/api/v1/plugins/<id>/`，`/api/v1/` 开头的宿主 API 只允许 GET（包括其它插件的 GET 路由，视为公开只读）。这是防误用的边界，不是安全边界（组件与主站同源）。请求用 `silent: true`，错误提示由插件自己决定；`locale` 把 WebUI 的 `en` 映射为 `en-US`；`theme.mode` 与 `theme.tokens` 是 getter，随深浅色实时取值；`i18n.t` 只翻译宿主文案，缺失时返回 key。接口形状未变，只补充了 `events.on` 的文档。
- **事件：SSE 新增 `bus` 帧**（后端 `api/events.py`）。每个 SSE 连接在总线上订阅 `*`：`inbox.changed` 仍驱动 `notification` 帧，其余事件以 `{"kind": ..., "payload": {...}}` 转发（`dataclasses.asdict`，不可序列化的字段转字符串），每连接最多积压 200 帧，连接重连期间发布的事件不补发。`host.events.on(kind, cb)` 只订阅总线事件，回调收到 `payload`；`status` / `downloader` 等快照帧不对插件开放。
- **错误边界按插件归因，不按元素**：custom element 回调、事件处理函数与 Promise 里抛出的错误不会经过 `append` 回到宿主，只会成为 `window` 的 `error` / `unhandledrejection`。宿主按脚本地址（`/plugins/<id>/web/`）把它们归给插件，该插件当时已挂载的所有挂载点一起显示「插件组件加载失败」，其它插件与页面不受影响；没有重试按钮，重新打开页面会重新导入。
- **挂载点位置**：`settings.section` 在设置页分区列表末尾追加（侧栏与搜索可见，`groups: []` 不参与全局保存）；`bangumi.detail.tab` 是番剧编辑弹窗里的 `ab-segmented` 标签（有插件标签时才出现，「规则」为原表单）；`bangumi.card.action` 是卡片标题下的操作条，而不是 `ab-menu` 下拉，因为插件元素自己渲染，不是 label / handler 菜单项，点击不触发卡片的编辑；`dashboard.widget` 在番剧列表页顶部的网格里；`page` 在侧边栏加入口（`Puzzle` 图标，排在设置之前）与路由 `/plugins/:id`，页面标题取清单标题。**移动端底部导航没有加插件页入口**（位置不够），手机上只能直接访问地址。
- **P4 遗留（a）：未启用插件的配置表单**。`PluginManager._probe_schemas()` 在 `start()` 与 `apply_settings()` 中，对内置插件和已开启 `allow_unsigned` 的插件导入代码取 `config_model` 后立即 `unload()`（不 `setup`、不注册扩展）；导入失败记为无 schema 并写日志，启用时再报告原因。未签名且未开 `allow_unsigned` 的插件仍不执行任何代码，schema 为空。因此首次启用前即可填写并保存配置（`PUT /plugins/<id>` 的校验同样可用）。
- **P4 遗留（b）：对象数组表单**。`schemaFields()` 为 `array` 且元素是对象的字段给出 `kind: 'objects'` 与 `itemFields`，`PluginSchemaForm` 递归渲染每一行并提供「添加一行 / 删除」；新行只带有默认值的字段，必填字段留空，由后端校验返回 422（界面只显示统一的保存失败提示）。
- **P4 遗留（c）：补链按钮由 `hardlink` 插件自己提供**，即 `settings.section` 元素 `ab-plugin-hardlink-backfill`（`web/index.js`，不构建的原生 ES module），调用插件自己的 `POST /backfill` 并显示四种计数。这样同时验证了内置插件也能带前端；未用宿主按钮。
- **示例插件 `examples/plugins/manual-pick/`**（不在 Docker 镜像内，README 说明复制到 `config/plugins/local/`）：`bangumi.detail.tab` 元素经宿主只读 API 列出规则的种子，选择经插件自己的 `PUT /picks/<bangumi_id>` 存入插件 KV 并发布 `manual-pick.picked` 事件，打开着的详情页经 `host.events.on` 刷新。SDK 0.x 没有「让下载器下载指定种子」的接口，所以插件只记录选择，不触发下载。
- **验证**：除 vitest / pytest 外，用 `vite preview`（带 CSP）加真实后端、系统 Chrome 无头跑过：详情页标签列出种子并选用、选择经 SSE `bus` 帧刷新、设置页补链按钮返回计数、`page` / `bangumi.card.action` 挂载点、崩溃与未定义元素显示失败提示，页面未报 CSP 违例。
- 踩坑：UnoCSS 的 attributify 会把源码里的 `` `[plugin:${id}]` `` 当成样式规则并让构建失败；`plugin-slot.vue` 里的日志不要用这种写法。

### 实施中的调整（P6 评审修复）

- **秘密字段掩码覆盖嵌套结构**（`module/plugin/secrets.py`）：`mask_options` / `restore_options` 沿 JSON Schema 递归（`$ref`、`anyOf` / `oneOf`、对象、数组 `items`、字典 `additionalProperties`），对象数组行里的 `secret_field()` 也会掩码。无 schema 时仍把全部字符串按秘密处理，现在同样递归。`secret_keys()` 无其它调用方，已删除；`/config/update` 改为使用返回值。
- **数组行没有稳定 id，还原按「掩码后内容相同」对应已保存的行**：删除、调换行不会串用密码。行内容也被改过时，行数未变则按位置对应；行数已变则无法确定，丢弃该掩码字段（密码留空，由插件的校验或用户重新输入处理），不取别行的密码。
- **未启用插件的 schema 每次重新发现后重新读取**（`_probe_schemas`）：插件目录升级后表单随之更新，首次导入失败也不再一直缓存为「无 schema」。代价是每次 `apply_settings` 会重新导入未启用的可信插件一次。
- **custom element 名归插件所有**：清单要求 `element` 为 `ab-plugin-<id>` 或以 `ab-plugin-<id>-` 开头。id 含连字符时命名空间会重叠（`foo` 的前缀也匹配 `ab-plugin-foo-bar`），`PluginManager.ui_slots()` 按全部已发现插件取 id 最长者为归属，其余声明被忽略并在重新发现时写警告日志。
- **前端按定义者校验元素**（`services/plugin-loader.ts`）：加载器包装 `customElements.define`，按调用栈里最近的 `/plugins/<id>/web/` 脚本地址记录每个名字由哪个插件定义；挂载点发现元素由其它插件定义时拒绝实例化并显示失败提示。这样插件即使在自己的模块里抢先定义别人的元素名，也拿不到别人挂载点的 `host`。归因依赖浏览器调用栈里带脚本地址（三大引擎都满足）；不经插件脚本定义的元素（定义者未知）不拦截。

### 实施中的调整（P7 第一部分：SDK 打包、命令行、契约套件与签名目录）

SDK 打包与清单：

- **`autobangumi-sdk` 轮子**：`backend/sdk/pyproject.toml` 用 setuptools，`package-dir` 指向 `../src`，只打包 `ab_sdk`，版本取 `ab_sdk.SDK_VERSION`。依赖 pydantic、httpx、packaging；可选依赖 `test` 为 pytest。构建命令：`uv build --wheel backend/sdk`。后端的 `dev` 依赖组以可编辑方式安装它（`tool.uv.sources`），所以 `uv run ab-plugin` 可用。生产依赖不变：Docker 的 `uv sync --frozen --no-dev` 不需要 `sdk/` 目录（已用只含 `pyproject.toml` 与 `uv.lock` 的目录验证）。`uv.lock` 的 `revision` 保持 3，因为 Docker 里的 uv 较旧。
- **清单解析移入 `ab_sdk.manifest`**：`ab-plugin` 与宿主共用，插件作者不必安装宿主。`module.plugin.manifest` 只再导出。保留 id 增加 `local`（`config/plugins/local/` 是本地插件目录，会与签名目录的 `config/plugins/<id>/` 冲突）。清单新增可选字段 `extension_points`，只用于签名目录展示，宿主以实际登记为准。`ab_sdk.manifest.check()` 校验清单、SDK 版本范围、入口模块、前端入口文件和原生扩展（`.so` / `.pyd` / `.dylib` / `.dll`），加载器、`ab-plugin` 与安装器都用它或其中的 `native_files()`。

`ab-plugin` 命令行（`ab_sdk/cli.py`，只依赖 `ab_sdk`）：

- **`new <id> [--kind rename|notifier|search]`**：生成 `plugin.toml`、包目录 `<id 的下划线形式>/__init__.py`（第 2.2 节布局）、`tests/test_contract.py`、仅用于开发的 `pyproject.toml` 和 README。生成的契约测试继承 `ab_sdk.testing` 的对应套件，测试用例对三种骨架各跑一遍。没有 `downloader` 骨架：下载器插件需要连接真实后端，一个能直接通过契约的骨架没有意义。
- **`validate [path]`**：`check()` 的结果；有问题时退出码为 1。
- **`pack [path] [-o dist]`**：先校验再打包。zip 内容在 zip 根，与 `llm-plugins` 包一致。排除 `tests/`、`pyproject.toml`、`uv.lock`、缓存和 `dist/`。文件顺序与时间戳固定，同样的内容得到同样的 sha256。
- **`dev [path] [--config-dir config]`**：软链到 `<config-dir>/plugins/local/<id>`，并在宿主配置文件（先找 `config_dev.json`，再找 `config.json`）中写入 `plugins.dev_mode`、`plugins.allow_unsigned` 和 `plugins.enabled.<id>`。配置文件不存在时拒绝执行，不创建残缺的配置：宿主看到配置文件就不再从环境变量初始化。运行中的 AutoBangumi 不会重读配置文件，需要重启一次。同一 id 已链接到别处时拒绝。

`dev_mode` 文件监听：

- 新配置项 `plugins.dev_mode`（默认 `false`）。开启后 `PluginManager` 每秒（`watch_interval`）对「应当运行的本地插件」计算文件指纹（相对路径、修改时间、大小，忽略 `__pycache__`），变化后重新发现并重载该插件。上次加载失败的插件也被监听，修好源码后自动恢复。基线在监听任务创建时同步取得，所以创建任务与首次轮询之间的修改不会漏掉。
- 新增 `PluginManager.reload(plugin_id)`：重新发现、卸载并加载一个插件，忽略配置快照。`apply_settings` 只在配置变化时重载，所以升级已安装插件（配置不变）要用它。
- 用轮询而不是 `watchfiles`，不增加依赖；只监听本地目录来源，不监听 pip 包，也不发现新出现的目录（要等下一次 `apply_settings` 或重启）。`GET /api/v1/plugins` 暂不返回 `dev_mode`，WebUI 的提示留给第二部分。

契约套件（`ab_sdk.testing`）：

- `DownloaderContract`、`RenameStrategyContract`、`NotifierContract`、`SearchSiteContract`。子类实现 `create()`，pytest 收集其中的 `test_*`。用例是同步的（内部 `asyncio.run`），不要求安装 pytest-asyncio；`ab_sdk.testing` 本身不 import pytest。
- `DownloaderContract` 总是检查结构（满足 `CoreDownloaderClient`、声明 `DownloaderCapabilities`、声明的能力都有对应方法）；行为检查（登录登出、添加种子、查询不存在的种子）只在子类设 `behavioral = True` 时运行。宿主里只有 `mock` 连着可用的后端，`qbittorrent` 与 `aria2` 只过结构检查。
- `NotifierContract` 的契约对象是 SDK 的 `Notifier`（`send(NotificationMessage)`）。宿主自带渠道接收整条配置和 `Notification`，测试里用一个适配器包装，并把 HTTP 层换成固定状态码的替身，所以 8 个内置渠道都验证了「后端拒绝时返回 `False` 而不抛异常」。
- 宿主侧 `test_provider_contracts.py` 验证 `mock` / `qbittorrent` / `aria2`、`none` / `pn` / `advance` / `template`（内置插件 `rename`）、8 个通知渠道和 4 个默认搜索站点。搜索站点没有以 `core` 登记（它们是 `search_provider.json` 的默认值），套件直接用 `DEFAULT_PROVIDER` 构造 `SearchSite`。这补上了 P4 推迟的 `RenameStrategyContract`。

签名目录来源（泛化 LLM 安装器）：

- **共用管线 `SignedCatalogInstaller`**（`module/plugin/installer.py`）：目录与插件包的验签、sha256、防 zip-slip、落盘到 `<root>/<id>/<version>/` 并写 `installed.json`。子类决定发布 tag、清单格式和安装后刷新。`PluginInstaller`（通用插件）用 tag `plugins`、目录 schema 2，条目含 `id`、`name`、`version`、`kind`、`extension_points`、`sdk`、`min_ab_version`、`asset`、`sha256`、`description`。LLM 安装器（`module/llm_plugins/installer.py`）变为同一基类的子类，tag 仍为 `llm-plugins`，清单仍为 `plugin.json`，行为和现有测试不变。
- **`module/llm_plugins/` 没有按第 8.3 节删除**：已发布的两个 LLM 插件（`plugins/codex-chatgpt`、`plugins/github-copilot`）仍是 `plugin.json` + `LLMProviderAdapter` 格式，要并入需要把它们改写为 `Plugin` + `llm_provider` Provider 并重新发布。这一步留到发布阶段。
- **加载器新增 `catalog` 来源**：优先级 builtin > catalog > local > pip。`config/plugins/<id>/installed.json` 指向的版本目录里有 `plugin.toml` 才算；`local` 目录、LLM 插件（只有 `plugin.json`）和损坏的指针都被忽略。`catalog` 来源视为已签名（`signed`），不受 `allow_unsigned` 限制。
- **路径安全**：`id` 会拼进文件系统路径。通用安装器在任何下载之前拒绝不符合 id 规则、保留的（`core`、`local`）和与内置插件同名的 id；卸载只删除存在 `installed.json` 的目录，所以 `DELETE /plugins/local` 不会删掉用户的本地插件。安装后用 `check()` 校验，清单的 id、版本必须与目录条目一致，`sdk` 范围必须包含当前 SDK 版本。
- **API**：`GET /api/v1/plugins/catalog`（目录条目加本机已装版本，目录不可达返回 502）、`POST /api/v1/plugins/{id}/install`、`DELETE /api/v1/plugins/{id}`。安装成功即写入 `plugins.enabled.<id> = true`（用户点了安装，视为同意它运行），再调用 `PluginManager.reload`；插件的必填配置缺失时进入错误状态，用户在表单中填写后恢复，与内置插件相同。`/plugins/{id}/install` 与 `/plugins/catalog` 由宿主注册在分发路由之前，因此插件自己的 `api_router` 不能使用 `install` 或 `catalog` 作为路由路径（与 P6 的 `web/` 同类限制）。
- **发布脚本** `scripts/build_plugin_catalog.py`：输入 `ab-plugin pack` 的 zip，输出 `catalog.json`、各 zip 及其 `.sig`（ed25519，base64），整个目录上传到 release `plugins`。测试用该脚本的产物走一遍安装器，保证两端格式一致。release `plugins` 本身与首批插件的上架留到发布阶段。

bark / wecom 旧字段别名：

- Bark 渠道不再读 `token`（只读 `device_key`），WeCom 不再读 `chat_id`（只读 `webhook_url`）。**直接删除会让 3.3 的配置静默失效**，所以 v3 → v4 迁移器把这两个旧字段搬到新字段：新字段为空时取旧值，两者都有时丢弃旧值（与 3.x 的 `新字段 or 旧字段` 一致）。WeCom 的 `token`（`key`）和其它渠道的 `token` / `chat_id` 不动。这一步与下载器等字段一样会备份 `config.json.v3.bak`。

### 实施中的调整（P7 第二部分：示例插件、文档与发布附件）

示例插件（`examples/plugins/`，不在 Docker 镜像内）：

- **6 个示例**：`manual-pick`（P6）、`webhook-on-event`、`custom-rss-site`、`template-rename`、`nfo-writer` 与计划外的 `ntfy-notifier`。设计文档要求「6 个以上」，任务列表只列了 5 个；补一个 `notifier` 示例，是为了让三个契约套件（重命名、通知、搜索站点）各有一个实物，文档的扩展点页也都有示例可指。
- **每个示例都是 `ab-plugin new` 的目录布局**（包目录、`tests/`、仅开发用的 `pyproject.toml`），可在示例目录里单独 `uv run pytest`。`nfo-writer` 取代原计划的 `jellyfin-refresh`：刷新媒体库已有内置插件 `media-server-refresh`。
- **「通过契约套件」只适用于有套件的三个**：`template-rename`（`RenameStrategyContract`）、`ntfy-notifier`（`NotifierContract`，含后端拒绝的用例）、`custom-rss-site`（`SearchSiteContract`）。`webhook-on-event` 与 `nfo-writer` 没有对应的 Provider 套件，用 `create_plugin` 写行为测试。契约套件当场发现了 `ntfy-notifier` 的一个真实缺陷（标题含中文时 httpx 的 `str` 请求头只接受 ASCII，`send` 抛 `UnicodeEncodeError`），修复为发送 UTF-8 的 `bytes` 请求头。
- **`template-rename` 不用 Jinja2**：内置 `template` 已用 Jinja2；第三方插件不能依赖宿主是否带 jinja2，所以示例自带 `{字段|过滤器:参数}` 的小语法与过滤器表（`pad`、`sanitize`、`short`、`upper`、`lower`）。渲染不出可用文件名时抛 `RenameSkipped`，不退回别的命名方式。
- **CI**：`scripts/test_example_plugins.sh` 对每个示例运行 `ab-plugin validate` 与它自己的测试（`-c <示例>/pyproject.toml --rootdir <示例>`，与作者在示例目录里运行一致），接入 `build.yml` 的 `test` 作业。`backend/src/test/test_plugin_examples.py` 另有一个宿主侧测试：把全部示例载入真实的 `PluginManager`，断言都进入 `active` 并登记了预期的 Provider 与钩子。该文件原有的 `manual-pick` 用例因此改为按 id 取状态。

文档（`docs/dev/plugins.md` 与 `docs/dev/plugins/`，中 / 英 / 日各一份）：

- `docs/dev/plugins.md` 保留为总览与导航（侧边栏链接不变），旧版 529 行的内容拆为 `plugins/` 下的页面：核心概念、配置表单、事件、前端挂载点、命令行、签名与分发、内置插件、示例，以及 `points/` 下每个扩展点一页（16 页：`mcp_tool` 与 `mcp_resource` 合一页，其余一点一页）。每种语言 25 个文件，侧边栏由 `docs/.vitepress/config.ts` 的一张页面表生成。`vitepress build` 通过（含死链检查）。
- **旧文档里与现状不符的地方一并改正**：下载器不再是 `downloader.type` 而是 `plugins.instances[].provider`；`hardlink` 的 `path_map` 已有对象数组表单；补链按钮已在 P6 提供；`file.renamed` / `torrent.organized` 加上 `downloader_id`。
- 签名与分发页如实写明：WebUI 的设置 → 插件页**还没有**目录浏览与安装按钮（只有 API），以及上架流程只有持有签名私钥的维护者能执行。「提 issue 申请上架」是文档里写的临时约定，没有对应的自动化。

插件作者 skill（`skills/autobangumi-plugin/`）：`SKILL.md`（触发描述、流程、扩展点速查表、易错规则）加 `references/` 三份（扩展点细节、测试 / CLI / 清单、前端）。内容面向模型，英文，与文档同源但不逐字复制。

发布接线（`.github/workflows/build.yml` 的 `release` 作业）：

- 新增两步：`uv build --wheel backend/sdk --out-dir sdk-dist` 与 `zip -r autobangumi-plugin-skill-<版本>.zip autobangumi-plugin`（在 `skills/` 下压缩，解压后得到 `autobangumi-plugin/` 目录）。`softprops/action-gh-release` 的 `files` 加入 `sdk-dist/*.whl` 与该 zip。轮子的版本是 `ab_sdk.SDK_VERSION`（目前 0.5.0），不是发布 tag 的版本。
- **「今天只有稳定版能创建 release」这一前提不成立**：`scripts/classify_release.py` 对 beta tag 已输出 `release=1`、`dev=1`，`release` 作业按 `dev == 1` 把 `prerelease` 设为 true，已有测试覆盖分类结果。所以没有改分类脚本与 Docker 标签（beta 仍推 `<版本>` 与 `dev-latest`）。新增一个测试，读 `build.yml` 断言 release 作业带预发布标志和两个新附件、skill 文件存在。
- 校验：`uvx check-jsonschema --builtin-schema vendor.github-workflows` 通过；`actionlint` 只报告已有步骤的 SC2086 提示（本次改动之前就存在）。
- **未验证**：轮子构建与 release 上传只在真实 tag 推送时才会被 CI 跑到；本地只验证了 `uv build --wheel backend/sdk`（第一部分）、YAML 语法与上面的测试。

### 实施中的调整（P7 评审修复）

- **原生扩展扫描与文件监听跳过工具链目录**：`native_files()` 原先遍历整个插件目录，`uv run pytest` 在插件目录里建出的 `.venv`（含 `pydantic_core` 的 `.so`）会让 `validate` / `pack` / `dev` 和宿主加载器都报「含原生扩展」，`dev_mode` 的指纹轮询也每秒遍历 `.venv`。`ab_sdk.manifest.TOOLING_DIRS`（`__pycache__`、`.git`、`.venv`、`dist`、`node_modules`、各类缓存）现在由原生扩展扫描、`pack` 与文件指纹共用；`pack` 仍额外排除 `tests`。
- **v3 迁移不再把 `null` 当作旧字段**：`Settings.save()` 总是把 Bark 的 `token`、WeCom 的 `chat_id` 以 `null` 写回，`old in provider` 因此每次启动都成立，每次启动都新增 `config.json.v3.bak.N` 并改写配置。现在只在旧字段有值时迁移。
- **通用插件与 LLM 插件共用 `config/plugins/<id>/` 的两处隔离**：LLM 注册表扫描跳过版本目录里是 `plugin.toml` 的目录（原先每次列举都对它打 `Skipping broken plugin` 警告）；通用安装器卸载时要求 `installed.json` 指向的版本目录含 `plugin.toml`，不能再通过 `DELETE /plugins/{id}` 删掉 LLM 插件（其凭据清理在 LLM 安装器里，不会被跳过）。
- **在线更新 bundle 带上 `ab_sdk`（PR 说明中的选项 2）**。`build.yml` 把 `backend/src/ab_sdk` 打进 bundle，`min_image_version` 设为 `4.0.0-beta.1`；`boot_overlay.py` 要求已验签 bundle 同时有 `module` 与 `ab_sdk` 两棵树，先换 `/app/ab_sdk` 再换 `/app/module`，缺一棵即不应用。已发布的 3.3 镜像在 beta 通道会选中最新预发布，但 3.3 的更新器在应用时检查 `min_image_version`（与 4.0 的代码相同，已有测试覆盖），拒绝后不留存 bundle，3.3 的 `boot_overlay` 因此不会应用它。两次替换不是一个事务：`ab_sdk` 换完而 `module` 失败时留下新 SDK 与旧 module。

未做（第一部分已列出，本部分也没有做）：

- **插件管理页**：设置 → 插件页没有目录浏览、安装 / 卸载按钮，也没有 `dev_mode` 提示；`GET /plugins` 仍不返回 `dev_mode`。任务清单不含它，推迟到发布阶段前补。
- **模板仓库**（含前端模板的独立 GitHub 仓库）：前端模板已在 `webui/packages/plugin-ui/template/`，`ab-plugin new` 覆盖后端骨架，独立仓库没有创建。
- **脚手架生成的 `pyproject.toml` 依赖 `autobangumi-sdk`** 但没有 uv 源：独立作者要等轮子上了 release 才能 `uv run pytest`。文档的上手步骤用 `uv tool install` 本地轮子文件绕过。

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
::: v-pre
- `template` 使用 Jinja2 沙箱模板，例如 `{{ title }} - S{{ season|pad(2) }}E{{ episode|pad(2) }}`。项目已依赖 Jinja2，能覆盖 80% 的定制需求。
:::
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
| **P2.5 多下载器** | 下载器多实例；`downloader_id` 列与迁移；按实例路由 add / rename / delete；organize 逐实例扫描 | 已完成：`plugins.instances` / `slots` 与 3.3 配置迁移器（`update/v4.py`）；按实例缓存客户端与路由投递、重命名、删除；重命名逐实例运行，不可用实例跳过并通知；WebUI 多实例管理与规则 / 订阅的下载器选择；单实例行为不变（全量测试）。qb + aria2 Docker e2e 未加，以进程内并存测试替代，调整见第 0 节 |
| **P3 流水线插件化：ingest** | `torrent.filter`、`title.parsed`、`torrent.adding`、`http.request` 钩子；`metadata_provider`（mikan / tmdb 以 `core` 登记）；内置插件 `ingest-filters`（包含过滤） | 已完成；无插件时行为不变（全量测试）。`feed_source`、`title_parser` 链、`admission_policy`、`matcher`、`ranker`、`save_path`、size 过滤、按订阅覆盖推迟，见第 0 节 |
| **P4 流水线插件化：organize** | `media_files`、`file_parser`、`rename_strategy`（含 `template`）、`conflict_policy`、`file.renamed` 等事件 | 已完成：`renamer.py` 拆出 `revision_saga.py`；`rename_strategy` / `media_files` / `conflict_policy` 扩展点与 `file.renamed` / `torrent.organized` 事件；内置插件 `rename`（pn / advance / template，pn / advance / none 输出与 3.3 一致）、`hardlink`（默认停用）与 `media-server-refresh`。`file_parser`、`RenameStrategyContract`、补链设置按钮（P6）推迟，调整见第 0 节 |
| **P5 事件与外部接口** | SSE 改订阅 bus；`api_router`、`mcp_tool` 扩展点；`message_template` | 已完成：系统事件上总线、通知中心 SSE 改为事件推送、插件路由 / MCP 工具与资源 / 通知模板；status 等快照类 SSE 仍按节拍采样。调整见第 0 节 |
| **P6 前端插件** | Web Component 挂载点、`AbHost` 桥接、错误边界、`/plugins/<id>/web` 静态资源、`@autobangumi/plugin-ui` 包 | 已完成：五个挂载点、`AbHost`、错误边界与 CSP；示例插件「手动选种」（`examples/plugins/manual-pick`）以详情页标签形式可用，内置 `hardlink` 的补链按钮走 `settings.section`；未启用插件的配置表单、对象数组表单、SSE `bus` 帧。调整见第 0 节 |
| **P7 生态** | 插件管理页（安装、启停、日志、错误）、签名目录发布流程、模板仓库（含前端模板）、`ab-plugin` CLI、文档（中 / 英 / 日） | 6 个以上示例插件上架。已完成：`autobangumi-sdk` 轮子、`ab-plugin` CLI（new / validate / pack / dev）、`dev_mode` 文件监听、四个契约套件、签名目录来源（`plugins` tag、`catalog` 加载来源、安装 API、发布脚本）、bark / wecom 旧字段迁移；6 个示例插件（CI 逐个运行）、中 / 英 / 日文档（总览加 24 页）、插件作者 skill、release 附带 SDK 轮子与 skill。**管理页的目录浏览 / 安装按钮与独立模板仓库未做**，留到 P8 前补，调整见第 0 节 |
| **P8 发布** | beta 测试、性能对比（RSS 刷新耗时、内存）、升级指南、`docs/changelog/4.0.md` | `4.0.0-beta.1` → `4.0.0` |

阶段依赖：P0 → P1 → P2 → (P2.5 ∥ P3 ∥ P4) → P5 → (P6 ∥ P7) → P8。P2.5、P3、P4 可并行，P6 依赖 P5 的 `api_router` 与事件总线。

## 11. 风险与待决问题

已决议题（SDK 版本、插件依赖、前端插件、多下载器）见第 0 节。剩余风险：

1. **性能**。每个种子都要经过多段 hook，RSS 一次可能有几百条。Filter hook 需要支持批量接口 `accept_many`，并加基准测试。
2. ~~**`release_replacement_lease` 无调用方**~~。已在 P4 删除：`set_state_claimed` 的同一条 UPDATE 写入状态并清除租约；异常退出的步骤只靠过期回收，最长占用一个租约周期（5 分钟，与重试冷却相同），只会推迟下一次尝试。
3. **翻译**。事件 `describe()` 当前硬编码中文。插件化后要走 i18n key，否则第三方插件消息无法翻译。前端组件通过 `host.i18n` 拿当前语言。
4. **多下载器的跨实例一致性**。同一番剧中途更换下载器时，已下载种子仍留在旧实例。renamer 按 `torrent.downloader_id` 路由即可，但 UI 要明确展示每个种子所在实例。此外不做跨实例迁移。
5. **前端插件的 0.x 期 API 变动**。`AbHost` 与挂载点同样遵循 SDK 0.x → 1.0 的节奏，4.0 期间可能调整，文档要标注。
6. **vendor 依赖冲突**。两个插件 vendor 同一个包的不同版本时，私有前缀隔离能避免冲突。但包内的绝对 import 可能需要重写，需要在 P2 验证可行性。若不可行，退回为「vendor 包加入全局 path，同名包先到先得并告警」。
