# [3.2.0-beta.6] - 2026-01-25

## Backend

### Features

- 新增番剧归档功能：支持手动归档/取消归档，已完结番剧自动归档
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
- 规则编辑弹窗新增归档/取消归档按钮
- 规则编辑器新增剧集偏移字段和「自动检测」按钮
- 新增 i18n 翻译（中文/英文）

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