# 命令行 ab-plugin

`ab-plugin` 随 `autobangumi-sdk` 轮子安装，只依赖 `ab_sdk`，不需要安装 AutoBangumi。

```bash
uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
# 或在项目里：uv add ./autobangumi_sdk-0.5.0-py3-none-any.whl
```

轮子在 4.0 beta / 正式版的 GitHub Release 附件中，不发布到 PyPI，见 [获取 SDK](/dev/plugins/sdk)。契约测试需要 pytest：`new` 生成的 `pyproject.toml` 已在 `dev` 依赖组里带上 pytest；自己建的项目用 `uv add --dev pytest`（或安装 `autobangumi-sdk[test]`）。

## new

```bash
ab-plugin new <id> [--kind rename|notifier|search] [--dir .]
```

生成 `<id>/` 目录：

```
<id>/
├── plugin.toml
├── <id 的下划线形式>/__init__.py   # 插件代码
├── tests/test_contract.py         # 继承 ab_sdk.testing 的契约套件
├── pyproject.toml                 # 仅用于开发，不会被打包
└── README.md
```

`id` 只能由小写字母、数字和连字符组成。目录已存在时拒绝执行。没有下载器骨架：下载器要连接真实后端，一个能直接通过契约的骨架没有意义。

生成的 `pyproject.toml` 依赖 `autobangumi-sdk`。这个包不在 PyPI 上，运行 `uv run pytest` 前先在插件目录里执行一次 `uv add <轮子路径>`，uv 会把依赖指向本地轮子。

## validate

```bash
ab-plugin validate [path]
```

校验清单字段、`sdk` 版本范围是否包含当前 SDK、入口模块是否存在、前端入口文件是否存在，并拒绝含原生扩展（`.so` / `.pyd` / `.dylib` / `.dll`）的目录。有问题时退出码为 1。

## pack

```bash
ab-plugin pack [path] [-o dist]
```

先校验，再打成 `dist/<id>-<版本>.zip`。zip 内容在 zip 根（与签名目录的包布局一致）。排除 `tests/`、`pyproject.toml`、`uv.lock`、`dist/`、`.venv`、`.git`、`node_modules`、各类缓存和 `.pyc`。文件顺序与时间戳固定：同样的内容得到同样的 sha256。

## dev

```bash
ab-plugin dev [path] [--config-dir config]
```

- 先校验，再把插件目录软链到 `<config-dir>/plugins/local/<id>`。
- `--config-dir` 默认是当前目录下的 `config`。在插件目录里运行时，请指向 AB 的配置目录（源码运行时为 `backend/src/config`）。
- 软链接指向插件目录的绝对路径，AB 必须能用同一路径访问它（例如源码运行的 AB）。AB 在 Docker 中运行时，请把插件目录复制或挂载到容器的 `config/plugins/local/<id>/`，再在 设置 → 插件 中开启「允许未签名插件」并启用它。
- 在宿主配置文件（先找 `config_dev.json`，再找 `config.json`）里写入 `plugins.dev_mode`、`plugins.allow_unsigned` 和 `plugins.enabled.<id>`。
- 配置文件不存在时拒绝执行：请先启动一次 AutoBangumi。
- 运行中的 AB 不会重读配置文件，需要重启一次。之后，`dev_mode` 每秒检查一次本地插件目录，文件变化后自动重载该插件。上次加载失败的插件也被监听，修好源码后自动恢复。
- `dev_mode` 只监听本地目录，不监听 pip 包，也不会发现新出现的插件目录（等下一次配置变更或重启）。

## 开发循环

```bash
ab-plugin new my-notify --kind notifier
cd my-notify
uv add ../autobangumi_sdk-0.5.0-py3-none-any.whl   # 只需一次
uv run pytest            # 契约测试
ab-plugin dev . --config-dir /path/to/autobangumi/config   # 链接并开启热重载，重启 AB 一次
# 改代码 → AB 自动重载 → 在 WebUI 里验证
ab-plugin pack .
```
