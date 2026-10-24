# Concepts

## Directory layout and manifest

```
config/plugins/local/my-plugin/     # the directory name must equal the id in the manifest
├── plugin.toml
├── my_plugin/                      # a package (or one my_plugin.py); relative imports work
│   └── __init__.py
├── web/                            # optional: frontend components (see Frontend slots)
└── vendor/                         # optional: pure-Python dependencies (no .so / .pyd / .dylib / .dll)
```

```toml
# plugin.toml
[plugin]
id = "my-plugin"              # lowercase letters, digits, hyphens; core and local are reserved
name = "My plugin"
version = "0.1.0"
sdk = ">=0.5,<1"              # ab_sdk version range
entry = "my_plugin:MyPlugin"  # module:Plugin subclass, relative to the plugin directory
description = "One sentence"
authors = ["me"]
permissions = ["network"]     # shown to the user only; not enforced
extension_points = ["notifier"]  # optional: shown in the signed catalog only
```

A plugin runs in the same process as AB and has full permissions. `permissions` is a declaration to the user. It is not a sandbox. `ab-plugin validate` checks the manifest, the SDK version range, the entry module and the frontend entry files.

## Plugin and configuration

- Inherit `Plugin[ConfigModel]` and set `config_model`. AB validates the user configuration with the model. The plugin gets a typed instance as `self.config`. A WebUI save with an invalid value is refused (HTTP 422).
- `async setup()` runs one time after loading. `async teardown()` runs one time before unloading. When the configuration changes, AB calls teardown, then builds the plugin again and calls setup. If `setup()` raises an exception, the plugin goes to the error state.
- For the form, see [Config forms](/en/dev/plugins/config-forms).

`self.ctx` gives all host abilities that a plugin can see:

| Attribute | Description |
| --- | --- |
| `plugin_id` | The plugin id |
| `config` | The validated config model instance (`None` if `config_model` is not set) |
| `log` | A logger with the prefix `plugin.<id>` |
| `kv` | A private persistent key-value store (`get` / `set` / `delete`); values must be JSON-serializable |
| `data_dir` | `config/plugin-data/<id>/`; AB creates it on first access |
| `bus` | The event bus: `publish(event)`, `subscribe(kind, handler)` |

Import only `ab_sdk` in a plugin. Do not import `module.*`. That code is internal to the host and can change at any time.

## The three extension declarations

| Decorator | Purpose |
| --- | --- |
| `@provider(point, id=...)` | A factory method that returns the implementation that the extension point defines. `id` is the name that the user selects |
| `@hook(point, priority=..., timeout=...)` | Attach to a filter or transform extension point of the host. On one point, hooks run in ascending `priority`, then by plugin id. The user can set the order with `plugins.hook_order` |
| `@subscribe(kind, timeout=...)` | Subscribe to events. `"*"` means all events. `timeout` overrides the default 30-second limit for one event |

A decorator only sets a marker. If an extension point name is wrong, the plugin fails to load and the plugin list shows the reason. AB does not ignore the error.

- A **filter hook** returns a `Verdict` (or a `bool`). One rejection stops the chain.
- A **transform hook** receives the result of the previous hook and returns a new value. `None` means no change. Hooks receive frozen snapshots. Use `dataclasses.replace` to return a changed copy.

## Isolation and circuit breaker

- Hooks, event handlers, scheduled tasks and route handlers have timeouts.
- An exception in a plugin does not affect the host. After 5 failures in a row, AB disables the plugin and shows the reason in the plugin list. A change to the plugin configuration starts a new load attempt.
- AB validates plugin return values inside the breaker. A value of the wrong type counts as a failure, and AB uses the default host behavior.
- Exception: `RenameSkipped` means "the input or the configuration has a problem". It does not count toward the breaker.

## Tests

`ab_sdk.testing` builds and drives a plugin without AB:

```python
from ab_sdk.testing import create_plugin

def test_filter(tmp_path):
    plugin, ctx = create_plugin(MyPlugin, {"key": "k"}, data_dir=tmp_path)
    ...
    assert ctx.bus.published == []
```

`create_plugin` validates the configuration with the host rules and builds the plugin (it does not call `setup`). `ctx.bus` records the events that the plugin publishes. `await ctx.bus.deliver(event)` delivers an event to the subscribers of the plugin.

For Provider extension points, the SDK has contract test suites. Inherit a suite and implement `create()`. pytest collects the test cases.

| Suite | Checks |
| --- | --- |
| `DownloaderContract` | A downloader client. With `behavioral = True` it also checks login, adding torrents and more |
| `RenameStrategyContract` | A rename strategy: returns a relative path inside the torrent, keeps the suffix, is deterministic |
| `NotifierContract` | A notification channel: `True` on success; `False` (not an exception) when the backend refuses |
| `SearchSiteContract` | A search site: the URL has one `%s`; the parser is `mikan` or `tmdb` |

```python
from ab_sdk.testing import RenameStrategyContract, create_plugin

class TestMyStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin(MyPlugin)
        return plugin.strategy()
```

The test cases are synchronous (they use `asyncio.run` inside). pytest-asyncio is not necessary.

## Publish as a pip package

Declare an entry point in the `pyproject.toml` of the package. Put `plugin.toml` in the **top-level package**:

```toml
[project.entry-points."autobangumi.plugins"]
my-plugin = "my_plugin:MyPlugin"
```

A plugin installed with pip is also unsigned. The user must turn on "Allow unsigned plugins". You cannot pip-install in the Docker image. Use a local directory there and put the dependencies in `vendor/`. For signed plugins, see [Signing and distribution](/en/dev/plugins/signing).
