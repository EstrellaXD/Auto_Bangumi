# Testing, CLI and manifest

## Manifest (`plugin.toml`)

```toml
[plugin]
id = "my-plugin"                 # ^[a-z0-9]+(-[a-z0-9]+)*$ ; not core/local
name = "My plugin"
version = "0.1.0"                # PEP 440
sdk = ">=0.5,<1"                 # must include the installed SDK version
entry = "my_plugin:MyPlugin"     # module:Class, relative to the plugin dir
description = ""
authors = []
permissions = ["network"]        # display only
extension_points = ["notifier"]  # display only (catalog)

[[plugin.ui]]                    # optional, see frontend.md
slot = "page"
element = "ab-plugin-my-plugin"
entry = "web/index.js"
title = { en-US = "My plugin" }
```

Layout: `plugin.toml`, `my_plugin/__init__.py` (or `my_plugin.py`), optional `web/`, `vendor/`, `tests/`, dev-only `pyproject.toml` (not packed).

## ab-plugin CLI

| Command | Effect |
| --- | --- |
| `ab-plugin new <id> [--kind rename\|notifier\|search] [--dir .]` | Skeleton with a contract test |
| `ab-plugin validate [path]` | Manifest, sdk range, entry module, web entry, native-file check; exit 1 on problems |
| `ab-plugin pack [path] [-o dist]` | Deterministic `dist/<id>-<version>.zip` (content at zip root; excludes tests, pyproject, caches) |
| `ab-plugin dev [path] [--config-dir config]` | Symlink to `config/plugins/local/<id>`, write `dev_mode`, `allow_unsigned`, `enabled.<id>`; needs an existing `config.json`/`config_dev.json`; restart AB once, then file changes reload the plugin |

## Tests

```python
import asyncio
from ab_sdk.testing import create_plugin

def test_x(tmp_path):
    plugin, ctx = create_plugin(MyPlugin, {"url": "https://x"}, data_dir=tmp_path)
    asyncio.run(plugin.on_event(event))        # call decorated methods directly
    assert ctx.bus.published == []             # events the plugin published
```

- `create_plugin` validates options through `config_model`, builds the plugin, does not call `setup()`. `ctx.kv` is an in-memory store; `await ctx.bus.deliver(event)` feeds the plugin's own subscriptions.
- Keep tests synchronous with `asyncio.run` so plain pytest works (no pytest-asyncio needed).
- Network: replace the HTTP client with `httpx.MockTransport` (expose a `client_factory` attribute on the plugin). Cover the backend-refusal path.
- Contract suites (subclass, implement `create()`): `DownloaderContract`, `RenameStrategyContract`, `NotifierContract` (+ `create_failing()`), `SearchSiteContract`. Run them through the real provider method, e.g. `create_plugin(Cls)[0].strategy()`.
- Write the failing test first; a contract failure usually points to a real bug (e.g. non-ASCII header values).

## Packaging and signing

- `ab-plugin pack` output is the unit for the signed catalog. Maintainers run `scripts/build_plugin_catalog.py` (ed25519 `.sig` for `catalog.json` and each zip) and upload to the `plugins` release. Authors cannot self-sign into the official catalog.
- pip distribution: entry point group `autobangumi.plugins`, with `plugin.toml` in the top-level package.
