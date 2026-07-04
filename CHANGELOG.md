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