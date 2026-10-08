# The ab-plugin Command

`ab-plugin` is installed with the `autobangumi-sdk` wheel. It depends only on `ab_sdk`. You do not need to install AutoBangumi.

```bash
uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
# or in a project: uv add ./autobangumi_sdk-0.5.0-py3-none-any.whl
```

The wheel is an attachment of the 4.0 beta and stable GitHub releases. It is not on PyPI. The contract tests need pytest: `uv add --dev pytest` (or install `autobangumi-sdk[test]`).

## new

```bash
ab-plugin new <id> [--kind rename|notifier|search] [--dir .]
```

Creates the directory `<id>/`:

```
<id>/
├── plugin.toml
├── <id with underscores>/__init__.py   # plugin code
├── tests/test_contract.py              # inherits a suite from ab_sdk.testing
├── pyproject.toml                      # for development only; not packed
└── README.md
```

The `id` can contain only lowercase letters, digits and hyphens. The command refuses if the directory exists. There is no downloader skeleton. A downloader needs a real backend, so a skeleton that passes the contract has no value.

## validate

```bash
ab-plugin validate [path]
```

Checks the manifest fields, that the `sdk` range includes the current SDK, that the entry module exists and that the frontend entry files exist. It refuses a directory that has native extensions (`.so` / `.pyd` / `.dylib` / `.dll`). The exit code is 1 if there are problems.

## pack

```bash
ab-plugin pack [path] [-o dist]
```

Validates, then creates `dist/<id>-<version>.zip`. The content is at the root of the zip, the same layout as a signed-catalog package. `tests/`, `pyproject.toml`, `uv.lock`, caches and `dist/` are excluded. File order and timestamps are fixed, so the same content gives the same sha256.

## dev

```bash
ab-plugin dev [path] [--config-dir config]
```

- Links the plugin directory to `<config-dir>/plugins/local/<id>` with a symlink.
- Writes `plugins.dev_mode`, `plugins.allow_unsigned` and `plugins.enabled.<id>` in the host config file (`config_dev.json` first, then `config.json`).
- Refuses if no config file exists. Start AutoBangumi one time first.
- A running AB does not re-read the config file. Restart it one time. After that, `dev_mode` checks the local plugin directories each second. When a file changes, AB reloads that plugin. AB also watches a plugin that failed to load, so it recovers after you fix the source.
- `dev_mode` watches local directories only. It does not watch pip packages. It does not find new plugin directories until the next config change or restart.

## Development loop

```bash
ab-plugin new my-notify --kind notifier
cd my-notify
uv run pytest            # contract tests
ab-plugin dev .          # link and enable hot reload; restart AB one time
# change code -> AB reloads -> check in the WebUI
ab-plugin pack .
```
