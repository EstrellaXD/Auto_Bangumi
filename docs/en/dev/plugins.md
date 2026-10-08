# Plugin Development

::: warning Preview SDK
The plugin SDK `ab_sdk` has a 0.x version during 4.0. Incompatible changes can occur. From 4.1 the SDK is frozen at 1.0 and follows semantic versioning. The `sdk` field in the manifest gives the version range your plugin needs. AB refuses to load an incompatible plugin.
:::

A plugin is a Python package, with optional frontend components. It runs inside the AutoBangumi process. A plugin can add downloaders, notification channels, search sites and rename methods. It can also add hooks to the pipeline, subscribe to events, and provide REST routes, MCP tools and settings-page UI.

## Five-minute start

1. Install the SDK and the command line. The wheel is an attachment of each 4.0 beta and stable release on [GitHub Releases](https://github.com/EstrellaXD/Auto_Bangumi/releases). The file name is `autobangumi_sdk-<version>-py3-none-any.whl`. The wheel is not on PyPI.

   ```bash
   uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
   ```

2. Create a skeleton and run its tests:

   ```bash
   ab-plugin new my-rename --kind rename   # or notifier, search
   cd my-rename && uv run pytest           # the skeleton includes a contract test
   ```

3. Link the plugin to your local AutoBangumi and enable hot reload. Start AB one time first, so that a config file exists in `config/`:

   ```bash
   ab-plugin dev .
   ```

   Restart AB one time. After that, AB reloads the plugin when you change its files.
4. Pack the plugin: `ab-plugin pack .` creates `dist/my-rename-0.1.0.zip`.

## Documentation map

**Basics**

- [Concepts](/en/dev/plugins/concepts): `Plugin`, `ctx`, the three extension declarations, the manifest, isolation and the circuit breaker
- [Config forms](/en/dev/plugins/config-forms): how `config_model` becomes a WebUI form
- [Events](/en/dev/plugins/events): system events, organize events and custom events
- [Frontend slots](/en/dev/plugins/frontend-slots): Web Components and `AbHost`
- [The ab-plugin command](/en/dev/plugins/cli): `new`, `validate`, `pack`, `dev`
- [Signing and distribution](/en/dev/plugins/signing): local plugins, the signed catalog, the release flow
- [Built-in plugins](/en/dev/plugins/builtin): `rename`, `hardlink`, `ingest-filters`, `media-server-refresh`
- [Example plugins](/en/dev/plugins/examples)

**Extension points**

| Extension point | Type | Purpose |
| --- | --- | --- |
| [Downloader](/en/dev/plugins/points/downloader) `downloader` | Provider | A new downloader backend |
| [Notifier](/en/dev/plugins/points/notifier) `notifier` | Provider | A new notification channel |
| [LLM provider](/en/dev/plugins/points/llm-provider) `llm_provider` | Provider | A new LLM parsing provider |
| [Search site](/en/dev/plugins/points/search-site) `search_site` | Provider | A site in the search box |
| [Scheduled task](/en/dev/plugins/points/scheduled-task) `scheduled_task` | Provider | A periodic task |
| [Metadata provider](/en/dev/plugins/points/metadata-provider) `metadata_provider` | Provider | The "parser" of an RSS subscription |
| [Rename strategy](/en/dev/plugins/points/rename-strategy) `rename_strategy` | Provider | The rule that makes file names |
| [Media files](/en/dev/plugins/points/media-files) `media_files` | Provider | Classify torrent files as media, subtitle or ignore |
| [Conflict policy](/en/dev/plugins/points/conflict-policy) `conflict_policy` | Provider | A new torrent version and an old torrent want the same file name |
| [REST routes](/en/dev/plugins/points/api-router) `api_router` | Provider | HTTP endpoints of the plugin |
| [MCP tools and resources](/en/dev/plugins/points/mcp) `mcp_tool` `mcp_resource` | Provider | Items for MCP clients |
| [Torrent filter](/en/dev/plugins/points/torrent-filter) `torrent.filter` | filter hook | Decide if a torrent is downloaded |
| [Parsed title](/en/dev/plugins/points/title-parsed) `title.parsed` | transform hook | Correct the title parse result |
| [Adding request](/en/dev/plugins/points/torrent-adding) `torrent.adding` | transform hook | Change save path, category and tags |
| [HTTP request](/en/dev/plugins/points/http-request) `http.request` | transform hook | Add a Cookie to the GET requests of AB |
| [Message template](/en/dev/plugins/points/message-template) `message_template` | transform hook | Rewrite push messages |

A plugin can also subscribe to events (`@subscribe`) and use a private key-value store and a data directory.
