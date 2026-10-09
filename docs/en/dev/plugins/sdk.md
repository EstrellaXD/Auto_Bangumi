# Get the SDK

The plugin SDK is not on PyPI. Each 4.0 beta and stable [GitHub release](https://github.com/EstrellaXD/Auto_Bangumi/releases) has two attachments for plugin authors:

| File | Content |
| --- | --- |
| `autobangumi_sdk-<SDK version>-py3-none-any.whl` | The `ab_sdk` package and the `ab-plugin` command |
| `autobangumi-plugin-skill-<AB version>.zip` | A plugin-development skill for AI coding assistants |

The wheel file name contains the SDK version (`ab_sdk.SDK_VERSION`, for example `0.5.0`). It does not contain the AB version. Download the wheel from the release of your target AB version, so that the two SDK versions are the same. The `sdk` range in the plugin manifest (for example `">=0.5,<1"`) must include this version.

## Install the wheel

The wheel needs Python 3.13 or later. It depends on `pydantic`, `httpx` and `packaging`. You do not need to install AutoBangumi.

To use only the command line, install the wheel as a global tool:

```bash
uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
ab-plugin --help
```

To write a plugin and run its tests, add the wheel as a dependency of the plugin project:

```bash
cd my-plugin
uv add ../autobangumi_sdk-0.5.0-py3-none-any.whl
uv run pytest
```

`uv add` writes the local path of the wheel in `[tool.uv.sources]` of `pyproject.toml`. `ab-plugin pack` does not pack `pyproject.toml` or `uv.lock`, so this path does not go into the plugin package. The `pyproject.toml` that `ab-plugin new` creates already needs `autobangumi-sdk`, but it gives no source. Thus, run `uv add` one time in a new skeleton too.

The contract tests need pytest. The `dev` dependency group of the skeleton already has pytest. You can also install the optional dependency `autobangumi-sdk[test]`.

To upgrade the SDK, download the wheel of the new release. Then run `uv tool install --force <new wheel>` or `uv add <new wheel>` again.

## Develop in the AB repository

The SDK source is in `backend/src/ab_sdk`. The package configuration is in `backend/sdk/pyproject.toml`. The `dev` dependency group of `backend` installs it in editable mode, so you do not need the wheel in the repository:

```bash
cd backend
uv sync --group dev
uv run ab-plugin validate ../examples/plugins/ntfy-notifier
```

To build the wheel yourself (the same command as CI):

```bash
uv build --wheel backend/sdk --out-dir sdk-dist
```

## The plugin-development skill

The skill is a set of Markdown instructions. An AI coding assistant reads them to write, test and pack AB plugins. The zip contains the directory `autobangumi-plugin/`:

```
autobangumi-plugin/
├── SKILL.md                    # workflow, extension point table, frequent errors
└── references/
    ├── extension-points.md     # signature and fields of each extension point
    ├── frontend.md             # frontend slots
    └── testing.md              # contract tests and create_plugin
```

Unpack it in the skills directory of your assistant. For Claude Code, the personal skills directory is `~/.claude/skills/`:

```bash
unzip autobangumi-plugin-skill-<AB version>.zip -d ~/.claude/skills/
```

For other assistants, use their skills directory. The source of the skill is `skills/autobangumi-plugin/` in the repository.

## How CI builds the files

The `release` job of `.github/workflows/build.yml` runs only when a maintainer pushes a version tag:

1. `uv build --wheel backend/sdk --out-dir sdk-dist` builds the wheel. The version comes from `ab_sdk.SDK_VERSION`.
2. The job zips `skills/autobangumi-plugin` into `autobangumi-plugin-skill-<AB version>.zip`.
3. The job attaches the two files to the GitHub release of that version, together with the WebUI, the online update bundle and other files. Beta (pre-release) and stable releases both have the two files.
