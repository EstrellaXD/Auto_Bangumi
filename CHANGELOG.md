# [3.3.1] - 2026-07-07

- **修复**：搜索/订阅/收集添加的种子未关联番剧被记成孤儿，导致孤儿记录无法通过 `track_orphans` 关闭；重复订阅时正确解析已存在的规则（不覆盖用户调好的 offset/filter），重新订阅已禁用的规则时自动重新启用；收集失败不再留下幽灵订阅规则
- **修复**（#721）：标题中的 Windows/qB 保留字符（`< > : " / \ | ? *`）会把保存路径拆成多级目录或丢字——生成保存路径时清洗（仅新订阅，不触碰既有做种库）
- **修复**（#667/#704）：总集篇等半集（12.5）不再被取整成第 12 集覆盖原文件，重命名保留小数（`S01E12.5`），通知同步保留
- **新增**（#904）：Server酱³ 推送支持——`sctp` 开头的 sendkey 自动走 `push.ft07.com` 端点
- **新增**（#147）：重命名完成的种子在下载器中打 `ab:renamed` 标签，供外部脚本（filebot / hlink 等）过滤已处理任务
- **新增**（#975 / #1042）：TMDB API Key 可自配（留空回退内置共享 key）；设置页新增"网络设置"面板（TMDB / Bangumi API 地址与 Key）

# [3.3.0] - 2026-07-07

3.3.0 正式版。主要变化（相对 3.2.x；逐项细节见下方 beta.1–beta.8 条目）：

- **全异步架构**：数据库层全面迁移到 `sqlite+aiosqlite`（WAL），仓储/服务/周期任务全部 async；组合根 `AppContext` 统一持有生命周期
- **下载器**：aria2 成为一等公民（能力协议 + 门面降级）；qBittorrent 4.x–5.2 全版本兼容
- **WebUI**：Soft Ink 组件体系整体重构（22 个通用组件）；种子管理页（孤儿/按番剧）；PT 站（NexusPHP）搜索源预设；Passkey 登录与自动弹出
- **LLM**：提供商插件框架（内置/预设/订阅/可下载分组），签名验证的插件安装管线；插件（GitHub Copilot / ChatGPT Codex）随 `llm-plugins` release 发布
- **更新系统**：ed25519 验签的在线更新与回滚
- **安全**：破坏性 GET 端点转 POST（CSRF）、路径穿越修复、JWT/Passkey 加固
- 剧场版/特别篇支持、每集偏移建议、通知中心等

### 自 beta.8 起新增

- **修复**（#1052）：批量抓取种子文件加节流，HTTP 429 时指数退避
- **修复**（#1053）：删除番剧时清理其派生的每番剧 RSS 订阅；搜索站订阅时正确映射站点对应的解析器
- **新增**：`track_orphans` 设置——关闭后不再记录未匹配种子（孤儿记录），后补规则可立即接住仍在源里的旧集

# [3.3.0-beta.8] - 2026-07-07

qBittorrent 5.x 全面兼容 + 种子管理页 + PT 站搜索源；日志不再"时有时无"。

## Backend

### Fixed

- **qBittorrent 5.x WebAPI 全面兼容**（对照 qB 各发布 tag 源码逐端点核验）：
  - qB 5.2 的 `torrents/add` 返回 JSON 计数（200/202）而非 "Ok."，此前每次成功投递都被记为失败并无限重试（beta.7 用户日志中的 `rejected torrent add: HTTP 200 …success_count:1` 与循环 409）；现正确识别 200/202/JSON/409，部分成功与 pending（URL 异步抓取）均按成功处理，409 对文件上传视为重复、磁力链经 hash 确认，无法确认时抛出留待重试
  - qB 5.0 把 `torrents/pause|resume` 改名为 `stop|start` 且无别名：此前对全部 5.x 暂停/恢复是静默空操作；现先试新名、404 时回退旧名并记住
  - `torrents/info?filter=paused` 在 5.x 被静默当作 All（MCP `list_downloads` 会返回全部种子）：paused/stopped 改为本地按 state 过滤
  - qB 5.2 空响应体统一回 204：`torrents/delete` 误报失败、`torrents/renameFile` 误判失败导致重命名每周期重试，均改为按 2xx 判定
  - `torrents/add` 同时发送 `paused` 与 `stopped` 参数（5.0 改名，双方各自忽略未知参数）
- **日志时有时无**：启动（容器重启/在线更新）时日志被整个删除，改为轮转进 `log.txt.1-3` 备份；轮转后 UI 只读 `log.txt` 导致历史瞬间清空，现预算内自动拼接备份尾部；轮转竞态不再可能炸掉 SSE 流；清空日志同时删除备份；总量上限约 8 MB
- **孤儿种子持续累积无处清理**（#818 / #885 / #1010，#1020 的 3.3 移植）：新增孤儿种子与按番剧种子的查询/删除端点

### Changed

- **Docker 镜像瘦身 208 MB → 160 MB（拉取体积 −24%）**：不再预编译字节码（root 属主 venv 下本就无法持久化）；去掉未使用的 `mcp[cli]` 附加依赖（typer/rich 等约 14 MB）

## Frontend

### Added

- **种子管理页**：番剧网格新增"未匹配种子"卡片（计数徽标），孤儿种子与按番剧种子列表支持多选、批量删除、一键清空（Promise 确认框）；规则编辑弹窗新增"查看种子"入口
- **PT 站（NexusPHP）搜索源预设**：添加搜索源对话框新增 PT 站模式，填站点地址 + Passkey +（可选）分类 ID 即可生成 `torrentrss.php` 搜索模板（分类用 `cat<ID>=1` 逐分类开关形式，纯数字校验，预览遮蔽 Passkey）；注意原生新版 NexusPHP 已停用 search 参数，请先在站点上确认 RSS 搜索可用
- **Passkey 自动弹出**：本浏览器成功用过 Passkey 后，打开登录页自动弹出认证；取消则本浏览器解除自动弹出（下次 Passkey 登录成功后重新记住），主动登出后的一次跳转不弹，避免反射式指纹确认又把用户登回去

### Fixed

- **登录页密码框按回车不登录**：登录按钮现在是表单的 submit 按钮（此前 type=button，双输入框表单无提交按钮时浏览器不做隐式提交）
- 下载页种子状态适配 qB 5.0+ 的 `stoppedDL/stoppedUP` 命名（此前显示原始状态串）

# [3.3.0-beta.7] - 2026-07-06

发版前 ship-readiness 审查（多代理评审 + 对抗验证）确认的 10 个缺陷全部修复；本版为 3.3.0 稳定版前的收尾修复版。

## Backend

### Fixed

- **保存设置可能静默写坏通知渠道密钥**：掩码密钥（`********`）按下标回填，删除/重排列表项后幸存项会错拿被删项的密钥且原值永久丢失。现按身份匹配回填（同下标同身份 → 全列表唯一身份 → 长度不变时按下标兜底），无法唯一定位来源时返回 400 提示重新输入密钥，绝不猜
- **生产构建下自托管 Inter 字体 404**：`/fonts` 未挂载静态目录，字体请求被 SPA 兜底路由回成 index.html，整站字体静默回退系统字体（开发模式由 Vite 直接服务 `public/`，故此前未暴露）
- **受限 UMASK（如 077）下在线更新后崩溃循环**：boot_overlay 以 root 解包/复制的文件是 600/700 root:root，以 ab 运行的应用读不了 `/app/module`。现每棵落地的树（module / dist / .venv，含 EXDEV 恢复路径）都交还应用用户，可读性与 UMASK 无关
- **EXDEV 就地替换非原子**：中途失败（磁盘满/IO 错误）会留下"删光了但没灌满"的残缺 module 树，启动进入必然 ImportError 崩溃循环。现先快照旧树到 `.ab_bak`，失败时恢复旧树再放弃本次覆盖
- **缺留存备份 bundle 时回滚会把 bundle.zip 换丢**：boot_overlay 下次启动判定 legacy/unsigned 整体清除覆盖层，实际落在镜像版本却报告"已回滚到上一版本"。现该场景改走"回退镜像版本"路径并如实报告，同时清掉无法验签的孤儿 backup 树
- **qBittorrent 凭据错误仍会累积触发 WebUI IP ban**："不重试"只在单次 auth 内生效，每个周期 tick 仍各发一次失败登录，约 5 次即被 qB 封禁 IP。现凭据被拒后进程级闩锁（保存设置后解锁重试）；auth 单飞化，并发等待者共享失败结论、不再补发 POST
- **下载器设置变更的生命周期竞态**：正在登录（尚未计入引用计数）的客户端不再被并发的设置变更块中途登出；连续两次改设置不再把第一个被撤下客户端顶掉导致连接池泄漏；`__aenter__` 中途被取消不再泄漏引用计数
- **entrypoint 属主迁移 marker 先写后 chown**：大海报缓存迁移中途被打断（停容器/崩溃/NAS 报错）会被记成"已完成"、之后每次启动跳过且永不自愈。现 `chown -R` 成功退出后才写 marker
- **aria2 下载列表在 WebUI 显示 undefined / NaNhNaNm**：`torrents_info` 载荷缺少下载页无条件消费的字段。现补齐 `num_seeds`/`num_leechs`（numSeeders/connections）、`eta`（qB 的 8640000=未知约定）、`added_on`（gid 映射入库时间，用于排序），并把 aria2 状态映射为 qB 状态词汇（active→downloading/uploading 等）

### Changed

- 程序控制端点（`/restart` `/start` `/stop` `/shutdown`）恢复 GET 别名（标记 deprecated，计划下个大版本移除）：3.2 及更早版本这些端点是 GET，外部自动化（cron / Home Assistant 等）升级后不应 405 静默失效

# [3.3.0-beta.6] - 2026-07-06

## Frontend

### Changed

- **Soft Ink 组件体系重构**：WebUI 的通用组件层整体重设计为"Soft Ink"语言——近单色的墨色文字 + 柔和填充控件，语义色只以小方块标记出现、不再承载文字（去掉粉彩胶囊标签、着色警告框、悬浮滑块分段器等模板化样式）
- 新增 22 个通用组件（`ab-button`/`ab-icon-button`/`ab-menu`/`ab-split-button`/`ab-modal`/`useConfirm()`/`ab-field`/`ab-input`/`ab-select`/`ab-switch`/`ab-segmented`/`ab-tag` v2/`ab-status` v2/`ab-badge`/`ab-progress`/`ab-alert`/`ab-empty`/`ab-skeleton`/`ab-list`/`ab-toolbar`/`ab-tooltip` 等），全部带 vitest 测试与 Storybook story；页面全量迁移，不再直接使用裸 `NButton`/`<button>`/`NPopconfirm`
- 弹窗统一为自适应 `ab-modal`（桌面居中对话框 / 移动端底部抽屉，焦点陷阱 + aria 语义 + 统一 footer 动作区）；破坏性操作统一走 Promise 式确认框
- 状态灯恢复"细线圆环 + 内部灯珠"形态并扩展为四态（运行/停止/暂停/降级）

### Fixed

- 触屏下按钮命中区统一保证 44px；键盘焦点环、屏幕阅读器标签（关闭/移除）等无障碍问题成批修复
- 下载器/代理设置的密码输入恢复 `autocomplete=off`，避免浏览器误填登录密码
- 深色主题下弹窗遮罩、通知徽标等硬编码颜色改走主题 token

### Removed

- 删除废弃组件：`ab-popup`、`ab-adaptive-modal`、`ab-label`、`ab-data-list`、`ab-add`、`ab-button-multi`、`ab-image`、`ab-rule`、`ab-swipe-container`，以及 `ab-input` UnoCSS 快捷类

# [3.3.0-beta.5] - 2026-07-05

## Backend

### Fixed

- 修复在线更新在 overlayfs/绑定挂载布局下"报告成功却停在旧版本"的问题：`boot_overlay` 用 `os.rename` 把 `/app/module` 换成新代码，而 `/app/module` 来自镜像的 overlayfs 下层，某些 overlay/内核组合拒绝跨挂载边界 rename 下层目录、抛 `EXDEV`（Errno 18），导致每次重启换码失败。现改为在遇到 EXDEV 时退回"就地替换目录内容"（逐文件触发 overlayfs copy-up），与挂载/overlay 拓扑无关；`dist` 树同理修复。**注意 `boot_overlay.py` 不随在线更新替换，此修复需拉取新镜像后方对后续更新生效**

## Frontend

### Changed

- "软件更新"卡片从日志页移到设置页（作为设置分区导航的最后一项）；日志页保留联系方式（About）卡片

# [3.3.0-beta.4] - 2026-07-05

## Backend

### Added

- `GET /api/v1/update/check` 新增 `force` 参数：用户主动点「检查更新」时绕过 15 分钟结果缓存重新拉取；进入设置页时的自动检查仍走缓存，避免频繁请求 GitHub API

### Changed

- 容器启动优化：LLM SDK（anthropic / openai / google-genai）由模块加载改为按需导入（仅在真正构造某提供商时才加载），把约 0.7s 移出启动路径——LLM 默认关闭时不再白付；实测 `parser.analyser` 包导入 782ms → 203ms
- entrypoint 递归 `chown /app/data /app/config` 改为按需执行：仅在首次启动、PUID/PGID 变更或卷根属主不符时才遍历（marker 记录），避免大海报缓存在 NAS 上每次启动的 O(文件数) 开销

## Frontend

### Fixed

- 修复登录成功后偶尔卡住不跳转（用户名/密码与 passkey 三种方式均受影响）：passkey 登录成功后从不导航（漏了 `router.replace`）；`useAuth.login` 未返回 promise 导致登录页无法 await 跳转；路由守卫在导航时 `await` setup 状态检查，初次检查失败后会阻塞之后的登录跳转——已登录时跳过该检查
- 会话过期（401）现在跳回登录页，而非停留在已失效页面看过期数据（含后台静默轮询的 401）；启动时的 token 刷新改为静默，过期不再在首屏闪错误提示

### Changed

- 「检查更新」给出主动反馈：已是最新/发现新版本各弹一条提示，并显示「上次检查 时间」（每次点击都刷新）；检查失败时展示后端的具体原因（限流/无匹配 Release）而非泛化文案

# [3.3.0-beta.3] - 2026-07-04

## Backend

### Added

- LLM 模型列表接口 `POST /api/v1/config/llm/models`：按所选提供商（OpenAI 兼容端点 / Anthropic / Gemini）在线拉取可用模型，供前端下拉选择；表单密钥为掩码时回退到已保存密钥；无密钥返回 400、提供商报错返回 502（细节仅进日志，不回显）
- 安装向导下载器连接测试支持 aria2：走 JSON-RPC `aria2.getVersion` 校验可达性与 RPC secret（此前只会探测 qBittorrent 登录接口，选 aria2 必然误报失败）

### Changed

- 日志去重：修复队列日志处理器沿用 Python 默认格式化、导致每行出现 `INFO::module.x:` 重复前缀的问题（显式声明为 `模块名: 消息`）；移除源码中 245 处手写 `[Tag]` 前缀（模块名已在行内）；去掉偏移扫描/日历刷新被上层重复记录的完成行；`Config loaded` 降为 DEBUG（每次保存/重启都会刷屏）
- LLM 默认模型 `gpt-4o-mini` → `gpt-5-mini`（旧模型已下架）；已保存配置不受影响

## Frontend

### Added

- 设置页与安装向导支持 aria2 下载器（类型选择 + RPC secret 填写提示）
- 编辑规则「高级设置」新增内容类型（剧集/剧场版/特别篇）、偏好字幕组、偏好分辨率——迁移 v10/v12 的既有后端能力此前无入口；剧场版/特别篇在规则信息标签中标出
- LLM 面板：模型输入改为可搜索、可自由输入的下拉，展开时按需从提供商 API 拉取模型列表，切换提供商/密钥/地址后自动重拉；新增超时/缓存/并发/熔断调优项（收进折叠区）
- 更新卡片新增「自动检查」开关；渠道与自动检查的改动即时持久化（直接写回配置，不触发重启）

### Changed

- 配置页重设计：左侧分区导航（搜索 + 未保存标记），单列分区取代原 4:7 双列布局；底部保存栏显示「N 处未保存修改 · 分区名」，命名「保存并重启」的后果，保存/放弃均二次确认，离开时若有未保存修改则拦截
- 日志页重设计：顶部错误/警告健康摘要 +「跳到第一条」；统一工具栏（级别筹码带实时计数 + 文本搜索 + 操作按钮）；行文本改中性色、仅按严重级别着色（修复暗色模式对比度 3.53:1 不达标）；拆出模块名单列显示；`overflow-wrap: anywhere` 修复长串割裂；联系方式收进紧凑 About 卡片
- 无障碍：配置项渲染真正的 `<label for>`，开关/下拉补 `aria-label`；日志级别筹码带 `aria-pressed`；移动端触控目标提升至 44px

### Fixed

- 统一确认弹窗：搜索源与 Passkey 删除由原生 `confirm()` 改为 NPopconfirm
- 下载器/代理密码输入框由明文改为密码框；修正占位符与文案（间隔字段的 `port` 占位符、qBittorrent 默认端口 8080、播放器 type/url 标签大小写、`admindmin` 占位符笔误）

# [3.3.0-beta.2] - 2026-07-03

## Backend

### Added

- 应用内在线自动更新：从项目 GitHub Release 下载 `update-bundle-<version>.zip`（校验 sha256 与 ed25519 签名，未签名的 Release 会被拒绝），把 module 源码树 + 前端 dist 作为覆盖层落地到持久卷 `config/updates/`，容器重建后仍保留；启动时由 entrypoint 的 `boot_overlay.py` 重新校验签名后比较“镜像基线 vs 覆盖层”版本，取较新者生效（依赖在应用阶段以非 root 身份按 uv.lock `uv sync`）；应用前自动快照数据库，回滚可恢复；新增鉴权保护端点 `GET /api/v1/update/check`、`POST /api/v1/update/apply`、`POST /api/v1/update/rollback`，进度经既有 SSE（`/api/v1/events/stream`）推送；新增 `update` 配置段（`channel` stable/beta、`auto_check`）。**需容器以 `restart: unless-stopped` 运行**——更新后进程自行退出，由 Docker 重启以应用覆盖层
- LLM 解析器支持多提供商（OpenAI 兼容端点/Anthropic Claude/Google Gemini）：`experimental_openai` 配置自动迁移到新的 `llm` 段（迁移用户默认 `mode=primary`，保持原有 LLM 优先语义）；新增 `mode` 解析模式开关——`fallback`（默认，正则优先，LLM 仅兜底）与 `primary`（LLM 优先，失败时正则兜底，不丢标题）；openai 提供商经 `base_url` 兼容 DeepSeek/Ollama/LM Studio/OpenRouter 等任意 OpenAI 格式端点

### Fixed

- 修复 qBittorrent 重命名校验在未看到新文件名时即报成功的问题（重试循环失效导致假阳性成功通知，#754 #749）
- 架构评审修复：下载器失败结果不再被误标为“已下载”（qB/aria2 统一返回 AddResult）；aria2 重命名后路径持久化、磁力 followedBy gid 迁移；生命周期状态切换加锁；安装向导完成后正确启动后台任务；LLM 调用增加超时/缓存/并发限制/熔断并走应用代理

## Frontend

### Added

- 日志页新增“软件更新”卡片：显示当前/最新版本与可更新徽标、渲染 Release 说明、稳定/测试渠道切换、检查与一键更新（带确认弹窗）、按 SSE 实时进度条、以及有备份时的回滚入口；含 `restart: unless-stopped` 要求与“重启中/需手动重启”状态提示
- 编辑规则新增「放送星期」选择器：移动端与键盘也能指定日历放送日（此前仅桌面拖拽可用）

### Changed

- 设置页 OpenAI 面板替换为 LLM 解析器面板：支持选择提供商（openai/anthropic/gemini）与解析模式，`base_url` 仅在 openai 提供商下显示
- 自托管 Inter 字体，移除阻塞渲染的 Google Fonts 外链（大陆网络环境首屏不再受 fonts.googleapis.com 拖累）；首页海报懒加载；日志页仅渲染最新 1000 行
- 移动端体验：底部导航真正固定在屏幕底部（此前实际渲染在内容顶部）；顶栏按钮、搜索筹码、弹窗关闭、偏移输入、设置向导等触控目标提升至 44px；RSS 订阅源错误信息在卡片内联显示（原为悬停提示）
- 无障碍：搜索结果与筛选项可键盘操作并带焦点样式、Esc 可关闭添加/编辑弹窗、空格键可激活卡片、退出登录改为真实按钮、搜索弹窗新增可见关闭按钮
- 设置向导：下载器连接测试不再强制通过才能继续（可先跳过测试稍后在设置页调整）、密码为空也可测试、用户名过短有内联提示、向导进度在页面刷新后保留（sessionStorage）
- 新增亮/暗主题警示色 token 并替换组件内硬编码颜色；添加 RSS 与通知设置的自绘开关/原生下拉替换为 naive-ui 控件

### Fixed

- 修复删除规则确认框的按钮语义陷阱：此前「否」也会删除规则（仅保留本地文件）且没有真正的取消按钮；现为明确的说明文案 +「同时删除已下载的文件」勾选 + 取消/删除双按钮
- RSS 订阅批量删除、下载器种子删除、清空日志、通知服务删除均增加确认弹窗
- 后台轮询（状态/日志/下载器/Passkey 列表）失败不再触发全局错误提示；下载器轮询失败保留上次数据而非清空为“无种子”；首页首次加载失败显示错误与重试而非新手引导；搜索连接失败与“无结果”区分显示；设置向导提交失败时展示后端具体原因
- 移动端 RSS 列表批量操作后勾选框与实际选中状态不再脱节

# [3.3.0-beta.1] - 2026-07-03

## Backend

### Added

- aria2 下载器升级为一等下载后端：真实的种子添加/查询/重命名/移动/删除支持（不再是仅返回占位结果的桩实现），新增 `aria2_gid` 表持久化 `ab:<bangumi_id>` 标签关联，供 `Renamer` 复用现有的按标签查偏移逻辑（迁移 v11）
- 支持剧场版/OVA/SP 等非剧集番剧的识别与整理：解析器可识别 剧场版/劇場版/电影版/Movie 及 OVA/OAD/SP/Special 等关键词，新增 `episode_type` 字段（迁移 v12）；剧场版按「标题 (年份)」平铺目录整理（不再嵌套 Season 子目录），特别篇归入第 0 季；TMDB 解析器在 `search/tv` 找不到匹配时回退查询 `search/movie`
- 新增番剧偏好字幕组/分辨率设置 (`preferred_group`/`preferred_resolution`，迁移 v10)：RSS 刷新时在同批次或与已下载种子比较，跳过明显更差的重复发布，未设置偏好的番剧行为不变
- 新增 SSE 推送端点 `GET /api/v1/events/stream`（鉴权保护），按原轮询节奏推送状态/下载器/日志事件

### Fixed

- 修复 `gen_save_path` 季度守卫的一处预置 off-by-one 缺陷：合法的 `season=0`（特别篇）此前会被误判并回退为原值并打印多余警告
- 收紧 `gen_save_path` 季度守卫：普通剧集在 `season_offset` 为负导致季号落到 0 时回退原季号（Season 0 会被 Plex/Jellyfin 当作特别篇），仅 `special` 类型允许合法落入第 0 季
- 撤销 `gen_path` 在重命名文件名前追加 `[字幕组] ` 前缀的改动（`group_tag` 恢复为仅影响 qBittorrent RSS 规则名）：避免已开启 `group_tag` 的用户升级后整个做种媒体库被批量重命名，破坏 Plex/Jellyfin 索引与 cross-seed/硬链接
- 修复多文件电影种子（正片 + 特典/花絮，BD 常见）所有文件生成相同目标文件名导致重命名互相冲突/覆盖的问题：体积最大的主文件使用「标题 (年份).ext」干净名，其余文件追加原始文件名词干作区分

## Frontend

### Changed

- 拆分超大组件：`ab-add-rss.vue`/`ab-edit-rule.vue` 提取出共享的 `useBangumiRuleForm` composable 及预览/标签/RSS 链接/过滤器/偏移量子组件；`calendar.vue` 拆分为 `calendar-board`/`calendar-day-column`/`calendar-card`/`calendar-mobile-list`/`calendar-rule-list-popup`
- 统一使用 naive-ui 原生组件（`NButton`/`NSelect`/`NSwitch`）替换自定义的 `ab-button`/`ab-select`/`ab-switch`/`ab-checkbox` 并删除后者
- 状态/下载器/日志轮询改为优先通过 SSE（`useEventStream`）获取更新，仅在 SSE 不可用或页面隐藏时才回退到定时轮询

# [3.3.0]

## Backend — Architecture

后端进行了一次以现代化和健壮性为目标的架构重构（行为与 REST API 保持兼容）：

### Changed

- 数据库层全面异步化：仓储层与 `Database` 迁移到 `sqlite+aiosqlite`（启用 WAL + busy_timeout），不再在事件循环上执行同步 DB 调用
- 组合优于继承：`Database` 不再继承 `Session`；`RSSEngine`/`TorrentManager`/`Renamer`/`SeasonCollector`/`SearchTorrent`/`RSSAnalyser` 改为构造函数注入依赖
- `Program` 上帝对象由 lifespan 组合根 `AppContext` + 通用 `PeriodicTask`/`Scheduler` 取代；启动流程改为 awaited（迁移失败会明确中止启动），下载器重试改为受监督的后台任务
- 迁移系统改为表驱动（`database/migrations.py`，声明式 `already_applied` 守卫），取代按版本硬编码的 if 链；版本号与 SQL 不变，旧库照常升级
- 下载器引入 `Downloader` Protocol + 能力标志；aria2 的部分支持如实声明（不再以 `NotImplementedError` 崩溃循环）
- 配置变更统一经由 `AppContext.reload_settings()` 生效（恢复了 RSS 规则的重新应用）
- 安全：会话存储加入过期清理，令牌比较改为常量时间比较

### Added

- qBittorrent 客户端会话复用：跨操作复用登录会话、401/403 自动重新认证，大幅减少重复登录 (#1039, #900)
- 可配置 TMDB / bgm.tv API Base URL，便于被墙用户使用镜像 (#1040, #1042)

### Fixed

- 修复下载器认证失败时 httpx 连接池泄漏
- 修复 OpenAI 解析阻塞事件循环（改用 AsyncOpenAI）
- 修复 `build_rss_rule` 的 `mustNotContain` 把过滤字符串按字符拆分而非按项做正则或运算
- 移除大量死代码（旧通知栈、SIGALRM 装饰器、空的 transmission 桩等）

# [3.2.8] - 2026-07-02

## Backend

### Fixed

- 修复 qBittorrent ≥ 5.2 登录失败：新版登录成功返回 HTTP 204 空响应体，旧代码要求 200 + "Ok." 导致认证失败 (#1044, #1034, #1043)
- 修复删除番剧/种子时文件不被删除：hashes 列表未按 qB API 要求以 `|` 拼接且响应状态未校验，删除失败现在会正确上报到 WebUI (#1046)
- 修复下载器认证失败时 httpx 连接池泄漏：连接失败后正确关闭客户端 (#1043)
- 加固初始设置接口：`/setup/test-downloader` 增加 URL 协议校验，所有 setup 接口不再回显原始错误详情 (#1041)
- 修复同一站点多个 RSS 并发请求触发 HTTP 429：按主机分组串行抓取并加入间隔，不同主机仍并行 (#1026)
- 修复 OpenAI 解析阻塞事件循环：切换到 AsyncOpenAI 异步客户端
- 修复番剧缓存的失效竞态：加锁并引入代数计数，防止过期快照覆盖较新的失效
- 修复无 `[字幕组]` 前缀的标题被解析器破坏 (#1025)
- 共享 httpx 客户端跟随 302 重定向（mikanime.tv 镜像域名） (#983)
- 修复 Linux 主机解析 Windows qBittorrent 保存路径导致季度总被置为 01 (#1016)
- 加固共享 httpx 客户端：缩短 keepalive 防止陈旧连接风暴 (#1018, #1028, #984)
- 删除 RSS 订阅时级联删除其种子记录，侧边栏不再残留条目 (#1019)
- 探测 qBittorrent 时遵循 SSL 设置 (#1014)

### Maintenance

- 发布包纳入 `pyproject.toml` / `uv.lock` / `requirements.txt` (#994, #1015)
- 容器启动 chown 跳过 `.venv`，加快启动 (#1011)

# [3.2.6] - 2026-03-01

## Backend

### Added

- 新增 `Security` 配置模型，支持登录 IP 白名单、MCP IP 白名单和 Bearer Token 认证
- 新增登录端点 IP 白名单检查中间件 (`check_login_ip`)
- MCP 安全中间件升级为可配置模式：支持 CIDR 白名单 + Bearer Token 双重认证
- 认证端点支持 `Authorization: Bearer` 令牌绕过 Cookie 登录
- 配置 API `_sanitize_dict` 修复：仅对字符串值进行脱敏，避免误处理非字符串字段

- 新增番剧放送日手动设置 API (`PATCH /api/v1/bangumi/{id}/weekday`)，支持锁定放送日防止日历刷新覆盖
- 数据库迁移 v9：`bangumi` 表新增 `weekday_locked` 列

### Fixed

- 修复 qBittorrent 下载器 SSL 连接问题：解耦 HTTPS 协议选择与证书验证，自签名证书不再导致连接失败 (#923)
- 修复 `torrents_rename_file` 重命名验证循环中 `continue` 应为 `break` 的逻辑错误

### Changed

- 重构认证模块：提取 `_issue_token` 公共方法，消除 3 处重复的 JWT 签发逻辑
- `get_current_user` 简化为三级认证（DEV 绕过 → Bearer Token → Cookie JWT）
- `LocalNetworkMiddleware` 重命名为 `McpAccessMiddleware`，从硬编码 RFC 1918 改为读取配置

### Tests

- 新增 101 个单元测试覆盖安全、认证、配置、下载器和 MockDownloader 模块

## Frontend

### Added

- 新增日历拖拽排列功能：可将「未知」番剧拖入星期列，自动设置放送日并锁定
  - 拖入后显示紫色图钉图标，鼠标悬停显示取消按钮
  - 锁定的番剧在日历刷新时不会被覆盖
  - 使用 vuedraggable 实现流畅拖拽动画
- 新增安全设置组件 (`config-security.vue`)，支持在 WebUI 中配置 IP 白名单和 Token
- 前端 `Security` 类型定义和初始化配置

---

# [3.2.3] - 2026-02-23

## Backend

### Added

- 新增 MCP (Model Context Protocol) 服务器，支持通过 Claude Desktop 等 LLM 工具管理番剧订阅
  - SSE 传输层挂载在 `/mcp/sse`，支持 MCP 客户端连接
  - 10 个工具：list_anime、get_anime、search_anime、subscribe_anime、unsubscribe_anime、list_downloads、list_rss_feeds、get_program_status、refresh_feeds、update_anime
  - 4 个资源：anime/list、anime/{id}、status、rss/feeds
  - 本地网络 IP 白名单安全中间件（RFC 1918 + 回环地址），无需 JWT 认证
- 新增通知系统重构，支持多通知渠道同时启用
  - 支持 Telegram、Bark、Server 酱、企业微信、Discord、Gotify、Pushover、Webhook 八种渠道
  - 新增通知管理 API：`GET/PUT /api/notification/providers`
- 新增 E2E 集成测试套件，覆盖 RSS→下载→重命名全流程

### Fixes

- 修复第 0 集（SP/OVA）被错误重命名为第 1 集的问题 (#977)
  - Episode 0 现在免受集数偏移影响，不再覆盖正常集数文件
- 修复 RSS 过滤器包含特殊字符（如 `[字幕组`）时导致程序崩溃的问题 (#974)
  - 无效正则表达式自动降级为字面量匹配
- 修复聚合 RSS 解析时 `title_raw` 为空导致 `TypeError` 崩溃的问题 (#976)
- 修复解析器处理无括号种子名称时 `IndexError` 崩溃的问题 (#973)
- 修复删除番剧时未清理关联种子记录的问题
- 修复认证路由、JWT 刷新和 WebAuthn 注册流程的多个安全问题
- 修复程序生命周期管理和后台任务取消逻辑
- 修复数据库迁移在部分场景下未正确执行的问题

### Performance

- 优化日志系统：`RotatingFileHandler` 轮转（5 MB × 3）、`QueueHandler` 异步写入、`GET /api/log` 限读 512 KB
- 优化重命名器：批量数据库查询，并发获取种子文件列表
- 所有 `logger.debug(f"...")` 转为惰性 `%s` 格式化（~80 处）

### Tests

- 新增 26 个回归测试覆盖 #974、#976、#977、#986
- 扩展 raw_parser、torrent_parser、path_parser 测试覆盖率

## Frontend

### Fixes

- 修复认证路由守卫和 i18n 初始化顺序问题
- 修复通知设置组件与项目设计系统的对齐问题
- 修复组件生命周期管理问题

## Docs

- README 移除未实现的 Aria2 和 Transmission 下载器 (#987)

---

# [3.2.0-beta.13] - 2026-01-26

## Frontend

### Features

- 重新设计搜索面板
  - 新增筛选区域，支持按字幕组、分辨率、字幕类型、季度分类筛选
  - 多选筛选器，智能禁用不兼容的选项（灰色显示）
  - 结果项标签改为非点击式彩色药丸样式
  - 统一标签样式（药丸形状、12px 字体）
  - 标签值标准化（分辨率：FHD/HD/4K，字幕：简/繁/双语）
  - 筛选分类和结果变体支持展开/收起
  - 海报高度自动匹配 4 行变体项（168px）
  - 点击弹窗外部自动关闭

---

# [3.2.0-beta.12] - 2026-01-26

## Backend

### Features

- 偏移检查面板新增建议值显示（解析的季度/集数和建议的偏移量）

### Fixes

- 修复季度偏移未应用到下载文件夹路径的问题
  - 设置季度偏移后，qBittorrent 保存路径会自动更新（如 `Season 2` → `Season 1`）
  - RSS 规则的保存路径也会同步更新
- 优化集数偏移建议逻辑
  - 简单季度不匹配时不再建议集数偏移（仅虚拟季度需要）
  - 改进提示信息，明确说明是否需要调整集数

---

# [3.2.0-beta.11] - 2026-01-25

## Backend

### Features

- 新增季度/集数偏移自动检测功能
  - 通过分析 TMDB 剧集播出日期检测「虚拟季度」（如芙莉莲第一季分两部分播出）
  - 当播出间隔超过6个月时自动识别为不同部分
  - 自动计算集数偏移量（如 RSS 显示 S2E1 → TMDB S1E29）
- 新增后台扫描线程，自动检测已有订阅的偏移问题
- 新增搜索源配置 API 端点：
  - `GET /search/provider/config` - 获取搜索源配置
  - `PUT /search/provider/config` - 更新搜索源配置
- 新增 API 端点：
  - `POST /bangumi/detect-offset` - 检测季度/集数偏移
  - `PATCH /bangumi/dismiss-review/{id}` - 忽略偏移检查提醒
- 数据库新增 `needs_review` 和 `needs_review_reason` 字段

## Frontend

### Features

- 新增搜索源设置面板
  - 支持查看、添加、编辑、删除搜索源
  - 默认搜索源（mikan、nyaa、dmhy）不可删除
  - URL 模板验证，确保包含 `%s` 占位符
- 新增 iOS 风格通知角标系统
  - 黄色角标 + 紫色边框显示需要检查的订阅
  - 支持组合显示（如 `! | 2` 表示有警告且有多个规则）
  - 卡片黄色发光动画提示需要注意
- 编辑弹窗新增警告横幅，支持一键自动检测和忽略
- 规则选择弹窗高亮显示有警告的规则
- 首页空状态新增「添加 RSS 订阅」按钮，引导新用户快速上手
- 日历页面海报图片添加懒加载，提升性能
- 日历页面「未知播出日」独立为单独区块，优化视觉节奏

### Fixes

- 修复移动端设置页面水平溢出问题
  - 输入框添加 `max-width: 100%` 防止超出容器
  - 折叠面板添加宽度约束和溢出隐藏
  - 设置栅格添加 `min-width: 0` 允许收缩
- 修复移动端顶栏布局
  - 搜索按钮改为弹性布局，填充 Logo 和图标之间的空间
  - 减小图标按钮尺寸和间距，优化紧凑型布局
  - 添加「点击搜索」文字提示
- 修复移动端搜索弹窗关闭按钮被截断问题
  - 减小弹窗头部内边距和元素尺寸
  - 搜索源选择按钮缩小至适配移动端
- 修复设置页面保存/取消按钮缺少加载状态
- 修复侧边栏展开动画抖动（rotateY → rotate）
- 移动端底部导航标签字号从 10px 增至 11px，提升可读性
- 登录页背景动画添加 `will-change: transform` 优化 GPU 性能

---

# [3.2.0-beta.8] - 2026-01-25

## Backend

### Features

- Passkey 登录支持无用户名模式（可发现凭证）

### Fixes

- 修复搜索和订阅流程中的多个问题
- 改进种子获取可靠性和错误处理

## Frontend

### Features

- Passkey 登录支持无用户名模式（可发现凭证）

---

# [3.2.0-beta.7] - 2026-01-25

## Backend

### Features

- 数据库迁移自动填充 NULL 值为模型默认值

### Fixes

- 修复下载器连接检查添加最大重试次数
- 修复添加种子时的网络瞬态错误，添加重试逻辑

## Frontend

### Features

- 重新设计搜索面板，新增模态框和过滤系统
- 重新设计登录面板，采用现代毛玻璃风格
- 日志页面新增日志级别过滤功能

### Fixes

- 修复日历页面未知列宽度问题
- 统一下载器页面操作栏按钮尺寸

---

# [3.2.0-beta.6] - 2026-01-25

## Backend

### Features

- 新增番剧归档功能：支持手动归档/取消归档，已完结番剧自动归档

### Fixes

- 修复 `add_all()` 方法缺少去重检查导致重复添加番剧规则的问题
- 去重逻辑基于 `(title_raw, group_name)` 组合，同时支持批量内部去重
- 新增剧集偏移自动检测：根据 TMDB 季度集数自动计算偏移量（如 S02E18 → S02E05）
- TMDB 解析器新增 `series_status` 和 `season_episode_counts` 字段提取
- 新增数据库迁移 v4：为 `bangumi` 表添加 `archived` 字段
- 新增 API 端点：
  - `PATCH /bangumi/archive/{id}` - 归档番剧
  - `PATCH /bangumi/unarchive/{id}` - 取消归档
  - `GET /bangumi/refresh/metadata` - 刷新元数据并自动归档已完结番剧
  - `GET /bangumi/suggest-offset/{id}` - 获取建议的剧集偏移量
- 重命名模块支持从数据库查询偏移量并应用到文件名

## Frontend

### Features

- 番剧列表页新增可折叠的「已归档」分区
- 日历页新增番剧分组功能：相同番剧的多个规则合并显示，点击可选择具体规则
- 番剧列表页新增骨架屏加载动画

### Fixes

- 修复弹窗 z-index 层级问题，新增 CSS 变量管理层级系统
- 改善无障碍体验：按钮最小触摸区域 44px、焦点状态可见、添加 aria-label
- 规则编辑弹窗新增归档/取消归档按钮
- 规则编辑器新增剧集偏移字段和「自动检测」按钮
- 新增 i18n 翻译（中文/英文）
- 优化规则编辑弹窗布局：统一表单字段对齐、统一按钮高度、修复移动端底部弹窗 z-index 层级问题
- 修复下载器页面仅显示季度文件夹名的问题，现在会显示「番剧名 / Season 1」格式

---

# [3.2.0-beta.5] - 2026-01-24

## Backend

### Features

- RSS 订阅源新增连接状态追踪：每次刷新后记录 `connection_status`（healthy/error）、`last_checked_at` 和 `last_error`
- 新增数据库迁移 v2：为 `rssitem` 表添加连接状态相关字段

### Performance

- 新增共享 HTTP 客户端连接池，复用 TCP/SSL 连接，减少每次请求的握手开销
- RSS 刷新改为并发拉取所有订阅源（`asyncio.gather`），多源场景下速度提升约 10 倍
- 种子文件下载改为并发获取，下载多个种子时速度提升约 5 倍
- 重命名模块并发获取所有种子文件列表，速度提升约 20 倍
- 通知发送改为并发执行，移除 2 秒硬编码延迟
- 新增 TMDB 和 Mikan 解析结果的内存缓存，避免重复 API 调用
- 为 `Torrent.url`、`Torrent.rss_id`、`Bangumi.title_raw`、`Bangumi.deleted`、`RSSItem.url` 添加数据库索引
- RSS 批量启用/禁用改为单次事务操作，替代逐条提交
- 预编译正则表达式（种子名解析规则、过滤器匹配），避免运行时重复编译
- `SeasonCollector` 在循环外创建，复用单次认证
- `check_first_run` 缓存默认配置字典，避免每次创建新对象
- 通知模块中的同步数据库调用改为 `asyncio.to_thread`，避免阻塞事件循环
- RSS 解析去重从 O(n²) 列表查找改为 O(1) 集合查找
- 文件后缀判断使用 `frozenset` 替代列表，提升查找效率
- `Episode`/`SeasonInfo` 数据类添加 `__slots__`，减少内存占用
- RSS XML 解析返回元组列表，替代三个独立列表再 zip 的模式
- qBittorrent 规则设置改为并发执行

## Frontend

### Features

- RSS 管理页面新增连接状态标签：健康时显示绿色「已连接」，错误时显示红色「错误」并通过 tooltip 显示错误详情

### Performance

- 下载器 store 使用 `shallowRef` 替代 `ref`，避免大数组的深层响应式代理
- 表格列定义改为 `computed`，避免每次渲染重建
- RSS 表格列与数据分离，数据变化时不重建列配置
- 日历页移除重复的 `getAll()` 调用
- `ab-select` 的 `watchEffect` 改为 `watch`，消除挂载时的无效 emit
- `useClipboard` 提升到 store 顶层，避免每次 `copy()` 创建新实例
- `setInterval` 替换为 `useIntervalFn`，自动生命周期管理，防止内存泄漏
- 共享 `ruleTemplate` 对象改为浅拷贝，避免意外的引用共变
- `ab-add-rss` 移除不必要的 `setTimeout` 延迟

### Fixes

- 修复 `ab-image.vue` 中 `<style scope>` 的拼写错误（应为 `scoped`）
- 修复 `ab-edit-rule.vue` 中 `String` 类型应为 `string`
- `bangumi` ref 初始化为 `[]` 而非 `undefined`，减少下游空值检查
- `ab-bangumi-card` 模板类型安全：动态属性访问改为显式枚举
- 启用 `noImplicitAny: true` 提升类型安全

### Types

- `ab-button`、`ab-search` 的 `defineEmits` 改为类型化声明
- `ab-data-list` 使用明确的 `DataItem` 类型替代 `any`

---

# [3.2.0-beta.4] - 2026-01-24

## Backend

### Bugfixes

- 修复从 3.1.x 升级后数据库缺少 `air_weekday` 列导致服务器错误的问题 (#956)
- 修复重命名模块中 `'dict' object has no attribute 'files'` 的错误
- 新增 `schema_version` 表追踪数据库版本，确保迁移可靠执行
- 修复 qBittorrent 下载器中缺少 `torrents_files` API 调用的问题

### Changes

- 数据库迁移机制重构：使用 `schema_version` 表替代仅依赖应用版本号的迁移策略
- 启动时始终检查并执行未完成的迁移，防止迁移中断后无法恢复

### Tests

- 新增全面的测试套件，覆盖核心业务逻辑：
  - RSS 引擎测试：pull_rss、match_torrent、refresh_rss、add_rss 全流程
  - 下载客户端测试：init_downloader、set_rule、add_torrent（磁力/文件）、rename
  - 路径工具测试：save_path 生成、文件分类、is_ep 深度检查
  - 重命名器测试：gen_path 命名方法（pn/advance/none/subtitle）、单文件/集合重命名
  - 认证测试：JWT 创建/解码/验证、密码哈希、get_current_user
  - 通知测试：getClient 工厂、send_msg 成功/失败、poster 查询
  - 搜索测试：URL 构建、关键词清洗、special_url
  - 配置测试：默认值、序列化、迁移、环境变量覆盖
  - Bangumi API 测试：CRUD 端点 + 认证要求
  - RSS API 测试：CRUD/批量端点 + 刷新
  - 集成测试：RSS→下载全流程、重命名全流程、数据库一致性
- 新增 `pytest-mock` 开发依赖
- 新增共享测试 fixtures（`conftest.py`）和数据工厂（`factories.py`）

---

# [3.1] - 2023-08

- 合并了后端和前端仓库，优化了项目目录
- 优化了版本发布流程。
- Wiki 迁移至 Vitepress，地址：https://autobangumi.org

## Backend

### Features

- 新增 `RSS Engine` 模块，从现在起，AB 可以自主对 RSS 进行更新支持 `RSS` 订阅并且发送种子给下载器。
  - 现在支持多个聚合 RSS 订阅源，可以通过 `RSS Engine` 模块进行管理。
  - 支持下载去重功能，重复的订阅的种子不会被下载。
  - 增加手动刷新 API，可以手动刷新 RSS 订阅。
  - 新增 RSS 订阅管理 API。
- 新增 `Search Engine`模块，可以通过关键词搜索种子并解析成收集或者订阅任务。
  - 插件化的搜索引擎，可以通过插件的方式添加新的搜索目标，目前支持 `mikan`、`dmhy` 和 `nyaa`
- 新增对字幕组的特异性规则，可以针对不同的字幕组进行单独设置。
- 新增 IPv6 监听支持，需要在环境变量中设置 `IPV6=1`。
- API 新增批量操作，可以批量管理规则和 RSS 订阅。

### Changes

- 数据库结构变更，更换为 `sqlmodel` 管理数据库。
- 新增版本管理，可以无缝更新软件数据。
- 调整 API 格式，更加统一。
- 增加 API 返回语言选项。
- 增加数据库 mock test。
- 优化代码。

### Bugfixes

- 修复了一些小问题。
- 增加了一些大问题。

## Frontend

### Features

- 增加 `i18n` 支持，目前支持 `zh-CN` 和 `en-US`。
- 增加 pwa 支持。
- 增加 RSS 管理页面。
- 增加搜索顶栏。

### Changes

- 调整一些 UI 细节。