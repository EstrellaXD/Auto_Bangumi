# 插件开发

::: warning 预览版 SDK
插件 SDK `ab_sdk` 在 4.0 期间为 0.x 版本，接口可能有不兼容调整；4.1 起冻结 1.0，之后遵守语义化版本。清单里的 `sdk` 字段声明你依赖的版本范围，AB 会拒绝加载不兼容的插件。
:::

插件是一个 Python 包（可带前端组件），在 AutoBangumi 进程内运行。插件可以增加下载器、通知渠道、搜索站点、重命名方式，也可以在流水线上挂钩子、订阅事件、提供 REST 路由、MCP 工具和设置页界面。

## 五分钟上手

1. 安装 SDK 与命令行。轮子随每个 4.0 beta / 正式版发布在 [GitHub Releases](https://github.com/EstrellaXD/Auto_Bangumi/releases) 的附件中（文件名 `autobangumi_sdk-<SDK 版本>-py3-none-any.whl`），不发布到 PyPI。详见 [获取 SDK](/dev/plugins/sdk)。

   ```bash
   uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
   ```

2. 生成骨架并测试。骨架的 `pyproject.toml` 依赖 `autobangumi-sdk`，而 PyPI 上没有这个包，所以先用 `uv add` 让它指向下载的轮子：

   ```bash
   ab-plugin new my-rename --kind rename   # 也可选 notifier、search
   cd my-rename
   uv add ../autobangumi_sdk-0.5.0-py3-none-any.whl   # 换成轮子的实际路径
   uv run pytest                                      # 骨架自带契约测试
   ```

3. 链接到本机的 AutoBangumi 并热重载。先启动过一次 AB，使它的配置目录下有配置文件；`--config-dir` 指向这个目录（源码运行时为 `backend/src/config`）：

   ```bash
   ab-plugin dev . --config-dir /path/to/autobangumi/config
   ```

   重启 AB 一次后，修改插件目录里的文件会自动重载。
4. 打包：`ab-plugin pack .` 生成 `dist/my-rename-0.1.0.zip`。

## 文档导航

**基础**

- [获取 SDK](/dev/plugins/sdk)：GitHub Release 中的轮子与插件开发 skill

- [核心概念](/dev/plugins/concepts)：`Plugin`、`ctx`、三种扩展声明、清单、隔离与熔断
- [配置表单](/dev/plugins/config-forms)：`config_model` 如何变成 WebUI 表单
- [事件](/dev/plugins/events)：系统事件、整理事件、自定义事件
- [前端挂载点](/dev/plugins/frontend-slots)：Web Components 与 `AbHost`
- [命令行 ab-plugin](/dev/plugins/cli)：`new`、`validate`、`pack`、`dev`
- [签名与分发](/dev/plugins/signing)：本地插件、签名目录、发布流程
- [内置插件](/dev/plugins/builtin)：`rename`、`hardlink`、`ingest-filters`、`media-server-refresh`
- [示例插件](/dev/plugins/examples)

**扩展点**

| 扩展点 | 类型 | 用途 |
| --- | --- | --- |
| [下载器](/dev/plugins/points/downloader) `downloader` | Provider | 新的下载器后端 |
| [通知渠道](/dev/plugins/points/notifier) `notifier` | Provider | 新的通知渠道 |
| [LLM 提供商](/dev/plugins/points/llm-provider) `llm_provider` | Provider | 新的 LLM 解析提供商 |
| [搜索站点](/dev/plugins/points/search-site) `search_site` | Provider | 搜索框的站点 |
| [定时任务](/dev/plugins/points/scheduled-task) `scheduled_task` | Provider | 周期执行的任务 |
| [元数据源](/dev/plugins/points/metadata-provider) `metadata_provider` | Provider | RSS 订阅的「解析器」 |
| [重命名方式](/dev/plugins/points/rename-strategy) `rename_strategy` | Provider | 文件名的生成规则 |
| [文件分类](/dev/plugins/points/media-files) `media_files` | Provider | 种子内文件分为正片、字幕、忽略 |
| [版本冲突策略](/dev/plugins/points/conflict-policy) `conflict_policy` | Provider | 新版本种子与旧种子争用文件名 |
| [REST 路由](/dev/plugins/points/api-router) `api_router` | Provider | 插件自己的 HTTP 接口 |
| [MCP 工具与资源](/dev/plugins/points/mcp) `mcp_tool` `mcp_resource` | Provider | 暴露给 MCP 客户端 |
| [种子过滤](/dev/plugins/points/torrent-filter) `torrent.filter` | filter 钩子 | 决定种子是否下载 |
| [修正解析结果](/dev/plugins/points/title-parsed) `title.parsed` | transform 钩子 | 修正标题解析 |
| [修改添加请求](/dev/plugins/points/torrent-adding) `torrent.adding` | transform 钩子 | 改保存路径、分类、标签 |
| [请求头](/dev/plugins/points/http-request) `http.request` | transform 钩子 | 给 AB 的 GET 请求加 Cookie 等 |
| [通知文案模板](/dev/plugins/points/message-template) `message_template` | transform 钩子 | 改写推送文案 |

此外，插件可以订阅事件（`@subscribe`），并使用私有的键值存储和数据目录。
