# AutoBangumi 项目分析报告

**版本**: 3.2.4 | **分析日期**: 2026-04-12

## 1. 项目概述

AutoBangumi 是一个基于 RSS 的动漫自动下载和整理工具。它监控动漫种子站点（Mikan、DMHY、Nyaa）的 RSS 源，通过 qBittorrent 下载剧集，并将文件整理为 Plex/Jellyfin 兼容的目录结构，支持自动重命名。

---

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.13 + FastAPI + SQLModel + SQLite |
| 前端 | Vue 3 + TypeScript + Naive UI + Vite + Pinia |
| 包管理 | `uv` (Python), `pnpm` (Node) |
| 部署 | Docker (Alpine 多阶段构建), 端口 7892 |
| CI/CD | GitHub Actions (测试 + Docker 多平台构建 + Telegram 通知) |

---

## 3. 项目结构

```
Auto_Bangumi/
├── backend/                # Python 后端 (FastAPI + SQLModel)
│   ├── src/
│   │   ├── main.py         # FastAPI 入口, API 挂载在 /api, MCP 挂载在 /mcp
│   │   └── module/         # 核心模块
│   │       ├── api/        # REST API 路由
│   │       ├── core/       # 应用控制器, 后台线程, 状态追踪
│   │       ├── conf/       # 配置管理, 常量, 日志
│   │       ├── database/   # SQLite 操作 (同步 + 异步引擎, 迁移)
│   │       ├── models/     # SQLModel/Pydantic 数据模型
│   │       ├── downloader/ # qBittorrent/Aria2 下载客户端抽象
│   │       ├── manager/    # 文件整理, 重命名, 种子管理
│   │       ├── mcp/        # Model Context Protocol 服务
│   │       ├── network/    # HTTP 客户端工具
│   │       ├── notification/ # 多渠道通知系统 (8个提供者)
│   │       ├── parser/     # 种子名解析, 元数据提取
│   │       ├── parser/analyser/ # TMDB, Mikan, OpenAI 解析器
│   │       ├── rss/        # RSS 源解析和分析
│   │       ├── searcher/   # 种子搜索 (Mikan, DMHY, Nyaa)
│   │       ├── security/   # JWT 认证, WebAuthn/Passkey, IP 白名单
│   │       ├── update/     # 版本迁移, 数据迁移, 启动例程
│   │       ├── checker/    # 健康/完整性检查
│   │       ├── utils/      # JSON 配置, 图片缓存, 数据工具
│   │       └── ab_decorator/ # 自定义装饰器
│   └── pyproject.toml
├── webui/                  # Vue 3 前端
│   ├── src/
│   │   ├── api/            # Axios API 客户端函数
│   │   ├── components/     # Vue 组件 (basic/, layout/, setting/, setup/)
│   │   ├── pages/          # 路由页面组件
│   │   ├── store/          # Pinia 状态管理
│   │   ├── router/         # Vue Router 配置
│   │   ├── hooks/          # 自定义 Vue 组合式函数
│   │   ├── i18n/           # 国际化 (zh-CN, en-US)
│   │   ├── services/       # 服务层 (webauthn.ts)
│   │   ├── style/          # 全局 SCSS 样式
│   │   └── utils/          # 工具函数
│   └── package.json
├── .github/workflows/      # CI/CD (build.yml)
├── docs/                   # VitePress 文档站
├── scripts/                # 工具脚本
├── Dockerfile              # 多阶段 Docker 构建
├── entrypoint.sh           # Docker 入口 (用户管理 + 应用启动)
├── CLAUDE.md               # Claude Code 指导文档
├── CHANGELOG.md            # 详细版本历史
└── CONTRIBUTING.md         # 贡献指南
```

---

## 4. 后端依赖

### 4.1 生产依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| fastapi | >=0.109.0 | Web 框架 / REST API |
| uvicorn | >=0.27.0 | ASGI 服务器 |
| httpx[socks] | >=0.25.0 | 异步 HTTP 客户端 (支持 SOCKS 代理) |
| httpx-socks | >=0.9.0 | SOCKS 代理连接器 |
| beautifulsoup4 | >=4.12.0 | HTML/XML 解析 (RSS 源) |
| sqlmodel | >=0.0.14 | ORM (Pydantic + SQLAlchemy 混合) |
| sqlalchemy[asyncio] | >=2.0.0 | 数据库工具包 (异步支持) |
| aiosqlite | >=0.19.0 | 异步 SQLite 驱动 |
| pydantic | >=2.0.0 | 数据验证 / 设置 |
| python-jose | >=3.3.0 | JWT 令牌创建/验证 |
| passlib | >=1.7.4 | 密码哈希 |
| bcrypt | >=4.0.1,<4.1 | Bcrypt 哈希后端 |
| python-multipart | >=0.0.6 | 表单数据解析 |
| python-dotenv | >=1.0.0 | 环境变量加载 |
| Jinja2 | >=3.1.2 | HTML 模板 (生产 SPA 服务) |
| openai | >=1.54.3 | OpenAI API 集成 (实验性解析器) |
| semver | >=3.0.1 | 语义化版本工具 |
| sse-starlette | >=1.6.5 | Server-Sent Events (MCP) |
| webauthn | >=2.0.0 | WebAuthn/Passkey 认证 |
| urllib3 | >=2.0.3 | HTTP 库 |
| mcp[cli] | >=1.8.0 | Model Context Protocol 服务 SDK |

### 4.2 开发依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| pytest | >=8.0.0 | 测试框架 |
| pytest-asyncio | >=0.23.0 | 异步测试支持 |
| pytest-mock | >=3.12.0 | 测试 Mock |
| ruff | >=0.1.0 | Python Linter |
| black | >=24.0.0 | Python 格式化 |
| pre-commit | >=3.0.0 | 预提交钩子 |

---

## 5. 前端依赖

### 5.1 生产依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| vue | ^3.5.8 | 核心框架 |
| vue-router | ^4.4.5 | 客户端路由 (Hash 模式) |
| pinia | ^2.2.2 | 状态管理 |
| vue-i18n | ^9.14.0 | 国际化 (zh-CN, en-US) |
| naive-ui | ^2.39.0 | UI 组件库 |
| axios | ^0.27.2 | HTTP 客户端 |
| @vueuse/core | ^10.11.1 | Vue 组合式工具 |
| @headlessui/vue | ^1.7.23 | 无头 UI 组件 |
| vuedraggable | ^4.1.0 | 拖拽列表组件 |

### 5.2 开发依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| vite | ^4.5.5 | 构建工具 / 开发服务器 |
| typescript | ^4.9.5 | 类型检查 |
| unocss | ^0.51.13 | 原子化 CSS 引擎 |
| vitest | ^0.30.1 | 单元测试框架 |
| storybook | ^7.6.20 | 组件开发/文档 |
| vite-plugin-pwa | ^0.16.7 | PWA 支持 |

---

## 6. API 路由 (`/api/v1/`)

| 路径 | 文件 | 端点功能 |
|------|------|----------|
| `/auth` | auth.py | 登录, 刷新令牌, 登出, 更新 |
| `/passkey` | passkey.py | WebAuthn 注册/认证 |
| `/log` | log.py | 日志访问 |
| `/program` | program.py | 启动/停止/重启/状态控制 |
| `/bangumi` | bangumi.py | 番剧 CRUD, 归档, 偏移检测, 星期管理, TMDB 集成 |
| `/config` | config.py | 配置读写 |
| `/downloader` | downloader.py | qBittorrent 客户端管理 |
| `/rss` | rss.py | RSS CRUD, 刷新, 分析, 订阅 |
| `/search` | search.py | 多提供者种子搜索 |
| `/setup` | setup.py | 首次运行设置向导 |
| `/notification` | notification.py | 通知提供者管理 |

---

## 7. 数据库设计

- **引擎**: SQLite (同步 + 异步 via `aiosqlite`)
- **数据路径**: `sqlite:///data/data.db`
- **ORM**: SQLModel (Pydantic v2 + SQLAlchemy)
- **Schema 版本**: 9 (自定义迁移系统)

### 数据表

| 表名 | 说明 |
|------|------|
| `bangumi` | 动漫系列信息 (标题, 年份, 季数, 保存路径, 偏移量, 星期, 海报等) |
| `rssitem` | RSS 源信息 (URL, 解析器, 连接状态, 最后检查时间) |
| `torrent` | 种子记录 (关联 bangumi_id 和 rss_id, 下载状态, qB 哈希) |
| `user` | 用户认证信息 |
| `passkey` | WebAuthn 凭证存储 |
| `schema_version` | 数据库迁移版本追踪 |

---

## 8. 核心后台线程

| 线程 | 说明 | 默认间隔 |
|------|------|----------|
| RSSThread | 定时 RSS 解析和种子添加 | 900s (15分钟) |
| RenameThread | 文件重命名循环 | 60s (1分钟) |
| OffsetScanThread | 后台偏移不匹配检测 | 6小时 |
| CalendarRefreshThread | Bangumi 日历数据刷新 | 24小时 |

---

## 9. 通知渠道 (8种)

telegram, discord, bark, server-chan, wecom, gotify, pushover, webhook

---

## 10. MCP 服务 (`/mcp`)

### 工具 (10个)

| 工具名 | 功能 |
|--------|------|
| list_anime | 列出所有动漫 |
| get_anime | 获取单个动漫详情 |
| search_anime | 搜索动漫 |
| subscribe_anime | 订阅动漫 |
| unsubscribe_anime | 取消订阅 |
| list_downloads | 列出下载任务 |
| list_rss_feeds | 列出 RSS 源 |
| get_program_status | 获取程序状态 |
| refresh_feeds | 刷新 RSS 源 |
| update_anime | 更新动漫信息 |

### 资源 (4个)

- `anime/list` - 动漫列表
- `anime/{id}` - 单个动漫
- `status` - 程序状态
- `rss/feeds` - RSS 源列表

### 安全

- 可配置 IP 白名单 (CIDR)
- Bearer Token 认证
- SSE 传输 (`/mcp/sse`)

---

## 11. 安全与认证

| 方式 | 说明 |
|------|------|
| JWT | 令牌通过 HttpOnly Cookie + Bearer Header 发放 (1天有效期) |
| WebAuthn/Passkey | 完整的 Passkey 注册和认证流程 |
| IP 白名单 | 可配置 CIDR 白名单 (登录和 MCP 端点) |
| Bearer Token | 静态令牌可绕过登录 (用于自动化) |
| DEV 模式 | `VERSION == "DEV_VERSION"` 时跳过认证 |

---

## 12. Docker 部署

### 构建

- **Builder 阶段**: `ghcr.io/astral-sh/uv:0.5-python3.13-alpine`
- **Runtime 阶段**: `python:3.13-alpine`
- 非 root 用户 `ab` (UID 911, GID 911)
- 通过 `tini` 进程管理器启动

### 运行

```yaml
services:
  AutoBangumi:
    image: ghcr.io/estrellaxd/auto_bangumi:latest
    ports:
      - "7892:7892"
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - PUID=1000
      - PGID=1000
    restart: unless-stopped
```

### 卷

| 路径 | 用途 |
|------|------|
| `/app/config` | 配置文件 (config.json) |
| `/app/data` | 数据库 + 海报缓存 |

---

## 13. CI/CD 流水线

`.github/workflows/build.yml` 包含 6 个 Job:

1. **test** - Python 测试 (pytest)
2. **webui-test** - 前端类型检查 (pnpm test:build)
3. **version-info** - 版本类型判断 (release/dev/build_test)
4. **build-webui** - Vue SPA 构建 (上传产物)
5. **build-docker** - 多平台 Docker 构建 (amd64 + arm64), 推送 DockerHub + GHCR
6. **release** - 创建 GitHub Release
7. **telegram** - Telegram 发布通知

---

## 14. 关键架构模式

1. **混合 ORM**: SQLModel 同时作为数据库表和 API 请求/响应 Schema
2. **双数据库引擎**: 同步引擎用于常规操作，异步引擎用于 Passkey 操作
3. **自定义 Schema 迁移**: 轻量级迁移系统 (非 Alembic)
4. **上下文管理器**: DownloadClient、RSSEngine 等使用 `__enter__`/`__exit__` 管理资源生命周期
5. **多继承组合**: `Program` 类继承所有后台线程能力
6. **环境变量展开**: 配置支持 `$ENV_VAR` 引用，凭据通过 `@property` 安全展开
7. **SPA 内嵌服务**: 生产模式下 FastAPI 直接服务 Vue 构建产物
8. **MCP 集成**: 通过标准 AI 工具接口管理动漫订阅
9. **可配置安全模型**: IP 白名单 + 静态 Bearer Token + JWT Cookie + WebAuthn 共存
10. **版本感知启动**: 级联决策树处理首次运行、遗留数据迁移、Schema 迁移
11. **种子标签**: 下载种子标记 `ab:<bangumi_id>` 用于重命名阶段关联
12. **双语响应**: API 响应同时包含 `msg_en` 和 `msg_zh`

---

## 15. 配置系统

- **文件**: `config/config.json` (生产) 或 `config/config_dev.json` (开发)
- **环境变量**: `AB_*` 前缀 (如 `AB_DOWNLOADER_HOST`, `AB_INTERVAL_TIME`)
- **配置节**: program, downloader, rss_parser, bangumi_manage, log, proxy, notification, experimental_openai, security
- **凭据安全**: 敏感字段尾部带下划线存储，通过 `@property` 展开 `$VAR` 环境引用

---

## 16. 开发命令速查

### 后端

```bash
cd backend && uv sync                        # 安装依赖
cd backend && uv run pytest                  # 运行测试
cd backend && uv run ruff check src          # Lint 检查
cd backend && uv run black src               # 代码格式化
cd backend/src && uv run python main.py      # 启动开发服务器 (端口 7892)
```

### 前端

```bash
cd webui && pnpm install                     # 安装依赖
cd webui && pnpm dev                         # 启动开发服务器 (端口 5173)
cd webui && pnpm build                       # 生产构建
cd webui && pnpm test:build                  # 类型检查
cd webui && pnpm lint                        # Lint 检查
```

### Git 分支规范

- `main`: 稳定发布版
- `X.Y-dev`: 活跃开发分支 (如 `3.2-dev`)
- Bug 修复 → PR 到当前版本 `-dev` 分支
- 新功能 → PR 到下一版本 `-dev` 分支
