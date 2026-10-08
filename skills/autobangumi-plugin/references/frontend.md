# Frontend (Web Component) slots

Plugin UI is a custom element defined by an ES module under `web/`. AB sets `element.host` (AbHost) and `element.context` before inserting it.

## Manifest

```toml
[[plugin.ui]]
slot = "bangumi.detail.tab"          # settings.section | bangumi.detail.tab | bangumi.card.action | page | dashboard.widget
element = "ab-plugin-<plugin-id>"    # must equal or start with ab-plugin-<plugin-id>-
entry = "web/index.js"               # under web/
title = { zh-CN = "…", en-US = "…" } # at least one language
```

`context`: `{ bangumiId }` for `bangumi.detail.tab` and `bangumi.card.action`; `{}` otherwise.

## AbHost

- `host.pluginId`
- `host.api.get/post/put/delete(path, ...)`: JSON in/out, rejects on non-2xx. Relative path = `/api/v1/plugins/<id>/…` (the plugin's own `api_router`). Paths starting `/api/v1/` are host APIs, GET only.
- `host.i18n.locale`, `host.i18n.t(key)`
- `host.theme.mode`, `host.theme.tokens` (`--ab-*`)
- `host.toast(message, "info" | "error")`
- `host.events.on(kind, cb) -> unsubscribe` (event bus; callback gets the event fields)

## Rules

- CSP is `script-src 'self'`: no inline scripts, `eval` or CDN scripts; bundle everything into the module. Images, styles and fetches are free.
- Use a Shadow DOM and `var(--ab-color-primary)`, `--ab-color-surface`, `--ab-color-text`, `--ab-radius-sm`, `--ab-font-mono` for theme-aware styling.
- Clean up in `disconnectedCallback` (call the unsubscribe function).
- Static files are served at `/api/v1/plugins/<id>/web/…` (login required, enabled plugins only). Do not use `web/` as an `api_router` path.
- An import failure or uncaught error shows "plugin component failed to load" for that plugin only.
- Build template: `webui/packages/plugin-ui/template/` in the AB repo (Vite library mode, one self-contained ES module to `web/index.js`). Types: `@autobangumi/plugin-ui` (`AbHost`, `AbPluginElement`, `AbSlotContext`); a workspace package, not on npm.
- Reference implementation: `examples/plugins/manual-pick/` (no build step).
