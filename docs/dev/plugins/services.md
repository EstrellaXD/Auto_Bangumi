# 下载与媒体库服务（SDK 0.7）

面向需要管理版本、补下载或独立整理媒体库的插件。通过 `self.ctx` 使用，无需导入 `module.*`、打开 AB 数据库或获取下载器凭据。清单声明 `sdk = ">=0.7,<1"`。

## 服务与责任

| 服务 | 用途 |
| --- | --- |
| `ctx.downloads` | 持久下载任务、文件快照、候选复查、幂等投递和对账 |
| `ctx.bangumi.get(id)` | AB 当前条目设置及季度、集数偏移；返回不可变快照 |
| `ctx.library` | 当前整理器与入库提交历史 |
| `ctx.metadata` | 使用宿主配置、代理和缓存查询 TMDB；区分 TV 与电影 |
| `ctx.maintenance` | 停任务、备份、记录进度、精确清理宿主下载历史 |
| `ctx.updates` | 用户指定 GitHub 来源的本地插件更新 |

版本选择、音乐与归档分类、路径映射、文件命名、旧文件接管预览和文件操作日志仍由插件负责。宿主不扫描整个媒体库来猜测文件归属。

## 下载任务与文件

```python
refreshed = await self.ctx.downloads.refresh()
page = await self.ctx.downloads.list_tasks(bangumi_id=entry_id, limit=100)
for task in page.items:
    if task.download_id not in refreshed.download_ids:
        continue
    files = await self.ctx.downloads.files(task.download_id)
    complete = [f for f in files.files if f.selected and f.progress >= 1]
```

- `download_id` 由下载器实例与远端 task ID 确定；`file_id` 由任务与下载器文件 index 确定。服务重建与 AB 重启不改变身份。
- 任务归属只来自已记录的投递、种子 hash 或 aria2 gid 关联。标题、共享目录、TMDB 身份与 qB 标签不能证明归属。按条目查询仅返回唯一归属该条目的任务。
- `association` 为 `matched`、`unmatched` 或 `ambiguous`。`associate(id, entry_id, revision=...)` 可人工绑定未关联任务，不能覆盖其他条目的归属或过期快照。
- 每个文件包含下载器路径、相对路径、大小、选择状态和独立完成度。`original_relative_path` 是宿主**首次观察**的名称；接管之前已被改名的旧文件无法据此还原发布名。
- 路径是下载器视角；插件负责将它映射到 AB 可访问的挂载路径。任务进度未到 100% 时也可整理已经完成的选中文件。
- 查询是持久快照。刷新失败的实例列在 `unavailable`，旧数据保留；空文件响应不会覆盖有效旧快照。仅 `refresh().download_ids` 中本轮成功观察的任务可启动整理。
- `cursor` 是一次遍历的分页位置，不是新增记录的时间水位。每页最多 500 条。历史任务和候选不会因一次远端空列表而被删除。

## 强制准入与幂等投递

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.admission import Admission

class Review(Plugin):
    @provider(points.DOWNLOAD_PREFLIGHT, id="gate")
    def gate(self):
        return self

    async def preflight(self, request):
        return Admission("hold", "Choose a version first")
```

在 **设置 → 插件 → 下载准入** 选择 `<插件 id>/gate`。未选择时沿用原生下载规则。所选插件被停用、丢失、超时、熔断或返回非法结果时保持 `held`，不会自动放行。RSS、手动添加、合集收集与 SDK 投递均经过 `DownloadClient.add_torrent` 的同一个入口。普通 `torrent.filter` 的 fail-open 语义不变。

选用强制准入时，RSS 整轮的原始候选会在全局过滤和首次投递之前保存。`AdmissionRequest.candidates` 是本次投递的候选；用其中的 `batch_id` 查询完整批次。`Candidate` 包含解析的季、集、版本、字幕组、清晰度、字幕与来源，以及匹配条目 ID、过滤阶段、原因和内容 revision。多个匹配条目不会被静默选成其中一个。

`recheck_candidates(bangumi_id=...)` 只重新解析、匹配和过滤，**不下载**。放宽全局过滤也不会自动批准历史候选。要补下载，先取得当前条目和候选快照，再调用：

```python
submission = await self.ctx.downloads.replay(
    candidate.id,
    candidate_revision=candidate.revision,
    mapping_revision=bangumi.revision,
    idempotency_key=f"choice:{candidate.id}:{candidate.revision}",
    policy_revision=await self.ctx.downloads.policy_revision(),
)
```

`replay` 重查当前过滤规则，拒绝过期、被过滤、未匹配或歧义候选。`submit(SubmitRequest(...), idempotency_key=..., policy_revision=...)` 用于插件自己的资源入口；插件必须提供当前条目快照，也仍经过所选强制准入。`submit` 不代替 RSS 的标题匹配；显式提交的条目属于调用方的选择。

意图在远端调用前落库，幂等键按插件隔离：

| 状态 | 含义 |
| --- | --- |
| `pending` | 正在准入或准备请求 |
| `held` / `rejected` | 未提交，等待选择或被策略拒绝 |
| `accepted` | 下载器确认受理；同一个键不重复投递 |
| `unknown` | 调用可能已生效，等待对账 |
| `failed` | 远端调用之前失败，可在修复后重试 |

同键不同资源会被拒绝。并发调用串行确认意图；存在资源重叠的未决意图时先 hold。`lookup_submission(key)` 对未知结果仅对账，查不到远端任务也不证明可以重投。`submissions(bangumi_id=...)` 提供共享只读意图列表，供版本策略处理其他入口的未决请求。

qB 磁力链与种子字节可在调用前确定 task ID。其他后端不能证明 ID 时，未知结果保留为未知，需人工检查；宿主不以猜测解除预留。每个资源单独使用幂等键最容易处理部分失败。已接受的 SDK 投递会同步进入原生种子历史。插件无需 qB label 来存储自己的处理状态。

## 独占媒体库整理器

用 `@provider(points.ORGANIZER, id="library")` 返回实现 `async organize(request)` 的对象，在设置中选择 `<插件 id>/library`。

- 默认 `native` 保持原生改名、硬链与事件流程。
- 选择插件后，原生重命名与内置硬链不处理这些任务。所选提供商不可用时暂停，无原生回退。
- 每次调用仅包含**一个下载任务、一个 AB 条目**及其文件快照。相同 TMDB 剧集的多个条目可输出到同一媒体目录，但不能借此遍历另一个条目的源文件。
- 每轮会重新提供任务。插件应按文件身份、完成度、映射和自己的日志处理增量；没有变化时返回 `None`。

```python
from ab_sdk.library import LibraryFile, OrganizeResult

# 完成自己的预览、冲突检查和实际文件操作后：
return OrganizeResult(
    operation_id="stable-operation-id-from-plugin-ledger",
    files=(LibraryFile(file.file_id, str(actual_library_path), "media"),),
    media_identity="tmdb:tv:123",
)
```

宿主检查文件属于本请求、已经完成且被选中，目标为绝对路径、普通文件、大小符合快照，并且条目映射仍有效。`kind` 可为 `media`、`subtitle`、`music` 或 `archive`。内容校验、覆盖策略、目标所有权和移动回滚由插件负责；宿主的大小检查不证明两个文件内容相同。

通过检查后先保存提交，再发布 `library.files_committed`。事件中的路径是实际媒体库目标，不是下载源目录。稳定的宿主 `operation_id` 按插件隔离；同 ID 不得更换内容。事件至少投递一次：失败会重试，进程重启会重放，订阅者需按 `operation_id` 去重。`ctx.library.commits()` 可分页补查，适用于晚加载的订阅者。内置媒体服务器刷新插件消费该事件。

## 元数据与映射变化

`ctx.bangumi.get(id)` 保留 AB 原生的 `season`、`season_offset`、`episode_offset`，同时提供 `effective_season`。`revision` 是设置内容摘要。插件不要再增加一套隐式偏移。

`bangumi.mapping_changed` 携带修改前后快照；插件收到后应让依赖旧映射的预览失效。事件为进程内通知，重新加载后仍应比较当前 revision。`ctx.metadata.search/get/episodes` 为可选 TMDB 查询，不要求每个 AB 条目先手动绑定 TMDB 才能整理。

## 维护与历史清理

从用户触发的 API 操作调用 `ctx.maintenance.run(name, callback)`。宿主停止周期任务，等待下载、整理及已入队事件完成，备份 SQLite、宿主配置和该插件私有目录，再执行 callback。通过 `progress.checkpoint(step, details)` 保存恢复位置。

成功后按之前运行状态恢复调度。失败或进程中断会留下持久记录，保持任务暂停；`operations/status` 可查询进度和备份位置。用户完成修复后调用 `resume(id)` 解除阻断，再通过 AB 的开始按钮恢复。它不代表媒体、下载器或数据库自动回滚。不要从周期任务、事件订阅者或另一个维护回调里启动维护。

`preview_history(entry_id, exact_release_ids)` 返回精确标题列表和 15 分钟有效的一次性 token。`clear_history(token)` 重新检查条目、策略、历史快照及未决下载，只删除选中的宿主种子历史并重置收集标记，不删除源文件、媒体库或下载任务关联。插件通过 `history.cleared` 清理自己的相关状态；通知失败会暂停，恢复时重试通知。原生下载意图会切换新的历史代次，允许用户明确重新下载。

`legacy_outputs(source_stat_identity, work_scope=absolute_directory)` 只读查询原生硬链插件已记录的源/目标 stat identity 与当前命名策略。它是接管提示，不是内容相等证明；不会扫描媒体库。完整启用预览、重命名计划与空目录清理由整理插件实现。

维护不是跨系统事务。插件自行停止它创建的后台写入任务，并记录可恢复的文件操作；备份也不包括整个媒体库或其他插件的私有文件。

## 本地插件更新

适用于 `config/plugins/local/<id>`。用户先启用未签名插件，再在该插件卡片填写固定的 GitHub `owner/repo`。宿主运行时每天检查最新稳定 Release，有新版通知，点击一次更新。不会自行推断或切换来源；签名市场的验证规则不变。

Release 附件格式：

```
<plugin-id>-<version>.zip
<plugin-id>-<version>.zip.sha256
```

tag 为 `1.2.3` 或 `v1.2.3`，ZIP 根目录包含 `plugin.toml` 与代码。SDK 的 `ab-plugin pack` 产物可用于 ZIP；另发布 SHA-256 文件。来源、插件 ID、旧/新版本、SDK 范围、校验和、大小限制与 ZIP 路径均经检查。checksum 随同仓库发布，不能代替作者签名；这是用户信任该仓库的本地更新。

下载和包校验成功后才进入维护屏障。加载新版失败时恢复旧代码、该插件私有目录及 KV，不覆盖整个 AB 数据库。备份保留在 `config/plugin-backups/<id>/<operation-id>`。中断更新使用 `updates.recover(operation_id)` 恢复，不能用普通 `maintenance.resume` 绕过代码恢复。设置页列出未完成维护与恢复按钮，包括代码目录丢失的更新。

## 从旧桥接迁移

1. 将 `sdk` 下限升为 0.7，改用不可变 DTO 和 `ctx` 服务，移除 ORM、下载器池、事件总线及配置对象的私有导入。
2. 将普通过滤中的强制审核迁到 `DOWNLOAD_PREFLIGHT`，将原生重命名后的目录扫描迁到 `ORGANIZER`。不要同时启用两套源文件整理。
3. 在插件 UI 中通过宿主设置接口选择提供商；切换会先停任务和备份。旧任务缺少精确关联时展示待确认并要求绑定，不能用目录名静默认领。
4. 保留已有插件文件日志，用 `legacy_outputs` 辅助生成接管预览；迁移确认之前不改媒体文件。插件数据库与文件操作仍需自己的幂等恢复。
5. 用 `create_plugin(..., downloads=..., bangumi=..., library=..., maintenance=..., metadata=..., updates=...)` 注入测试替身。`DownloadPreflightContract` 与 `OrganizerContract` 提供返回值检查；仍需覆盖并发、超时、增量和恢复行为。

可运行的准入示例见 [download-review](https://github.com/EstrellaXD/Auto_Bangumi/tree/4.0-dev/examples/plugins/download-review)。
