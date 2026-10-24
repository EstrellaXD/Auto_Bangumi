# 核心概念

## 目录结构与清单

```
config/plugins/local/my-plugin/     # 目录名必须与清单中的 id 相同
├── plugin.toml
├── my_plugin/                      # 包（或单个 my_plugin.py）；内部可用相对导入
│   └── __init__.py
├── web/                            # 可选：前端组件（见「前端挂载点」）
└── vendor/                         # 可选：纯 Python 依赖（禁止 .so / .pyd / .dylib / .dll）
```

```toml
# plugin.toml
[plugin]
id = "my-plugin"              # 小写字母、数字、连字符；core、local 为保留 id
name = "我的插件"
version = "0.1.0"
sdk = ">=0.5,<1"              # 依赖的 ab_sdk 版本范围
entry = "my_plugin:MyPlugin"  # 模块:Plugin 子类，相对插件目录
description = "一句话说明"
authors = ["me"]
permissions = ["network"]     # 仅向用户展示，不做强制
extension_points = ["notifier"]  # 可选：只用于签名目录的展示
```

插件与 AB 在同一进程中运行，拥有完整权限。`permissions` 只是向用户声明，不是沙箱。`ab-plugin validate` 会校验清单、SDK 版本范围、入口模块和前端入口文件。

## Plugin 与配置

- 继承 `Plugin[配置模型]` 并设置 `config_model`。AB 按模型校验用户配置，插件通过 `self.config` 拿到带类型的实例。在 WebUI 保存不合法的值会被拒绝（HTTP 422）。
- `async setup()` 在加载后调用一次，`async teardown()` 在卸载前调用一次。配置变更时，插件先 teardown，再重新构造并 setup。`setup()` 抛出异常会让插件进入错误状态。
- 配置如何变成表单，见 [配置表单](/dev/plugins/config-forms)。

`self.ctx` 是插件看到的全部宿主能力：

| 属性 | 说明 |
| --- | --- |
| `plugin_id` | 插件 id |
| `config` | 已校验的配置模型实例（未声明 `config_model` 时为 `None`） |
| `log` | 带 `plugin.<id>` 前缀的 logger |
| `kv` | 插件私有的持久化键值存储（`get` / `set` / `delete`），值须可 JSON 序列化 |
| `data_dir` | `config/plugin-data/<id>/`，首次访问时创建 |
| `bus` | 事件总线：`publish(event)`、`subscribe(kind, handler)` |

插件只应 import `ab_sdk`，不要 import `module.*`：后者是宿主内部实现，随时可能重构。

## 三种扩展声明

| 装饰器 | 用途 |
| --- | --- |
| `@provider(point, id=...)` | 工厂方法，返回该扩展点约定的实现。`id` 是用户选择它时用的名字 |
| `@hook(point, priority=..., timeout=...)` | 挂到宿主声明的 filter / transform 扩展点。同一扩展点上按 `priority` 升序执行，相同时按插件 id；用户可用 `plugins.hook_order` 指定顺序 |
| `@subscribe(kind, timeout=...)` | 订阅事件，`"*"` 表示全部事件。`timeout` 覆盖默认 30 秒的单个事件处理超时 |

装饰器只打标记。扩展点名写错时，插件加载失败并在插件列表显示原因，不会被悄悄忽略。

- **filter 钩子**返回 `Verdict`（或 `bool`），任一拒绝即短路。
- **transform 钩子**接收上一个钩子的结果并返回新值；返回 `None` 表示不修改。传给钩子的都是冻结快照，用 `dataclasses.replace` 返回修改后的副本。

## 隔离与熔断

- 钩子、事件处理、定时任务和路由处理函数都有超时。
- 插件抛出异常不会影响宿主。同一插件连续失败 5 次会被自动禁用，并在插件列表显示原因；修改该插件的配置后会重新尝试加载。
- 插件返回值在熔断保护内校验：类型不对按失败处理，并回退到宿主的默认行为。
- 例外：`RenameSkipped` 表示「输入或配置有问题」，不计入熔断。

## 测试

`ab_sdk.testing` 可以在不启动 AB 的情况下构造并驱动插件：

```python
from ab_sdk.testing import create_plugin

def test_filter(tmp_path):
    plugin, ctx = create_plugin(MyPlugin, {"key": "k"}, data_dir=tmp_path)
    ...
    assert ctx.bus.published == []
```

`create_plugin` 按宿主的规则校验配置并构造插件（不调用 `setup`）。`ctx.bus` 记录插件发布的事件；`await ctx.bus.deliver(event)` 把事件同步投递给插件自己的订阅者。

对 Provider 类扩展点，SDK 提供契约测试套件。继承它并实现 `create()`，pytest 会收集其中的用例：

| 套件 | 检查对象 |
| --- | --- |
| `DownloaderContract` | 下载器客户端；`behavioral = True` 时加跑登录、添加种子等行为检查 |
| `RenameStrategyContract` | 重命名方式：返回种子内的相对路径，保留扩展名，结果确定 |
| `NotifierContract` | 通知渠道：发送成功返回 `True`；后端拒绝时返回 `False` 而不是抛异常 |
| `SearchSiteContract` | 搜索站点：URL 含一个 `%s`，解析器为 `mikan` 或 `tmdb` |

```python
from ab_sdk.testing import RenameStrategyContract, create_plugin

class TestMyStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin(MyPlugin)
        return plugin.strategy()
```

套件里的用例是同步的（内部 `asyncio.run`），不要求安装 pytest-asyncio。

## 以 pip 包发布

在包的 `pyproject.toml` 中声明 entry point，并在**顶层包内**附带 `plugin.toml`：

```toml
[project.entry-points."autobangumi.plugins"]
my-plugin = "my_plugin:MyPlugin"
```

pip 安装的插件同样未签名，需要开启「允许未签名插件」。Docker 镜像无法 pip 安装，此时请使用本地目录，并把依赖放进 `vendor/`。签名插件见 [签名与分发](/dev/plugins/signing)。
