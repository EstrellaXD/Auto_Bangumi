# 获取 SDK

插件 SDK 不发布到 PyPI。每个 4.0 beta 与正式版的 [GitHub Release](https://github.com/EstrellaXD/Auto_Bangumi/releases) 都附带两个给插件作者的文件：

| 文件 | 内容 |
| --- | --- |
| `autobangumi_sdk-<SDK 版本>-py3-none-any.whl` | `ab_sdk` 包与 `ab-plugin` 命令行 |
| `autobangumi-plugin-skill-<AB 版本>.zip` | 给 AI 编码助手使用的插件开发 skill |

轮子文件名里是 SDK 版本（`ab_sdk.SDK_VERSION`，如 `0.5.0`），不是 AB 的版本号。请从目标 AB 版本的 Release 下载轮子，两者的 SDK 版本一致。插件清单里的 `sdk` 范围（如 `">=0.5,<1"`）必须包含这个版本。

## 安装轮子

轮子要求 Python 3.13 或更高，依赖 `pydantic`、`httpx` 与 `packaging`，不需要安装 AutoBangumi。

只用命令行时，装成全局工具：

```bash
uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
ab-plugin --help
```

写插件和跑测试时，把轮子加为插件项目的依赖：

```bash
cd my-plugin
uv add ../autobangumi_sdk-0.5.0-py3-none-any.whl
uv run pytest
```

`uv add` 在 `pyproject.toml` 的 `[tool.uv.sources]` 里记下轮子的本地路径。`ab-plugin pack` 不打包 `pyproject.toml` 与 `uv.lock`，这个路径不会进入插件包。`ab-plugin new` 生成的 `pyproject.toml` 已经依赖 `autobangumi-sdk`，但没有指定来源，所以在新骨架里也要先执行一次 `uv add`。

契约测试需要 pytest。骨架的 `dev` 依赖组已带上 pytest；也可以安装可选依赖 `autobangumi-sdk[test]`。

升级 SDK 时，下载新 Release 的轮子，再执行一次 `uv tool install --force <新轮子>` 或 `uv add <新轮子>`。

## 在 AB 仓库里开发

SDK 的源码在 `backend/src/ab_sdk`，打包配置在 `backend/sdk/pyproject.toml`。`backend` 的 `dev` 依赖组以可编辑方式安装它，所以在仓库里不需要轮子：

```bash
cd backend
uv sync --group dev
uv run ab-plugin validate ../examples/plugins/ntfy-notifier
```

自己构建轮子（与 CI 相同的命令）：

```bash
uv build --wheel backend/sdk --out-dir sdk-dist
```

## 插件开发 skill

skill 是一组 Markdown 说明，AI 编码助手读取它们来写、测试和打包 AB 插件。zip 内是 `autobangumi-plugin/` 目录：

```
autobangumi-plugin/
├── SKILL.md                    # 工作流程、扩展点一览、常见错误
└── references/
    ├── extension-points.md     # 每个扩展点的签名与字段
    ├── frontend.md             # 前端挂载点
    └── testing.md              # 契约测试与 create_plugin
```

把它解压到助手的 skills 目录。以 Claude Code 为例，个人 skills 目录是 `~/.claude/skills/`：

```bash
unzip autobangumi-plugin-skill-<AB 版本>.zip -d ~/.claude/skills/
```

其它助手请按它们各自的 skills 目录放置。skill 的源码在仓库的 `skills/autobangumi-plugin/`。

## CI 如何构建

`.github/workflows/build.yml` 的 `release` 任务只在维护者推送版本标签时运行：

1. `uv build --wheel backend/sdk --out-dir sdk-dist` 构建轮子，版本取自 `ab_sdk.SDK_VERSION`。
2. 把 `skills/autobangumi-plugin` 压缩为 `autobangumi-plugin-skill-<AB 版本>.zip`。
3. 把两者与 WebUI、在线更新包等文件一起附到该版本的 GitHub Release。beta（预发布）与正式版都带这两个文件。
