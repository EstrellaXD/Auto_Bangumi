# Frontend Slots

A plugin can mount its own UI at fixed places in the WebUI. The UI is a standard Web Component (custom element). An ES module defines the element. AB creates it and passes `host` and `context`. No frontend framework is necessary. To use Vue, Lit or a similar library, bundle it into your module.

## Manifest

```toml
[[plugin.ui]]
slot = "bangumi.detail.tab"
element = "ab-plugin-manual-pick"
entry = "web/index.js"
title = { zh-CN = "手动选种", en-US = "Manual pick" }
```

- `slot`: the slot. See the table below.
- `element`: the custom element name. It must be `ab-plugin-<plugin id>` or start with `ab-plugin-<plugin id>-`. The plugin owns this namespace. A plugin cannot define the element names of another plugin.
- `entry`: the ES module that defines the element. It is in `web/`.
- `title`: the title for each language, at least one. AB uses it as the tab name, the page title or the settings section name.

If the manifest is not valid, AB refuses the whole plugin. `ab-plugin validate` checks that the entry file exists.

## Slots

| `slot` | Position | `context` |
| --- | --- | --- |
| `settings.section` | The end of the settings section list; visible in the sidebar and in search | `{}` |
| `bangumi.detail.tab` | An extra tab in the series edit dialog (the segmented control appears only when a plugin tab exists) | `{ bangumiId }` |
| `bangumi.card.action` | The action bar under the title of a series card | `{ bangumiId }` |
| `page` | An extra sidebar entry with the route `/plugins/<id>`; the page title is the manifest title | `{}` |
| `dashboard.widget` | The grid at the top of the series list page | `{}` |

The mobile bottom navigation has no entry for plugin pages. On a phone, open the address directly.

## Component and AbHost

AB sets the `host` and `context` properties before it inserts the element. You can use them in `connectedCallback`.

```js
class MyWidget extends HTMLElement {
  async connectedCallback() {
    const root = this.attachShadow({ mode: 'open' });
    root.innerHTML = `<button>${this.host.i18n.locale}</button>`;
    root.querySelector('button').onclick = async () => {
      const data = await this.host.api.get('stats');      // /api/v1/plugins/<id>/stats
      this.host.toast(JSON.stringify(data));
    };
    this.off = this.host.events.on('my-plugin.changed', () => this.refresh());
  }
  disconnectedCallback() { this.off?.(); }
}
customElements.define('ab-plugin-my-plugin', MyWidget);
```

| Member | Description |
| --- | --- |
| `host.pluginId` | The plugin id |
| `host.api.get/post/put/delete` | Requests with the login session. They return parsed JSON and reject for a non-2xx status. A path that does not start with `/` is relative to `/api/v1/plugins/<id>/`. A path that starts with `/api/v1/` is a host API and allows GET only (public read-only, including GET routes of other plugins) |
| `host.i18n.locale` | The current language, for example `zh-CN`, `en-US` |
| `host.i18n.t(key, params?)` | Translate a host text. Returns the key if it is not found |
| `host.theme.mode` / `host.theme.tokens` | The current light/dark mode and the values of the `--ab-*` variables. They follow the theme live |
| `host.toast(message, kind?)` | Show a message (`info` or `error`) |
| `host.events.on(kind, callback)` | Subscribe to events on the event bus. The callback gets the event fields. Returns an unsubscribe function. AB also unsubscribes when the component unmounts |

AB refuses paths that leave the plugin scope (`..`, `//host`, full URLs). This is a guard against mistakes. It is not a security boundary: the component has the same origin as the main site, so the plugin has full permissions. Requests show no error message by default. The plugin decides how to show errors.

## Styles

AB puts the component in a Shadow DOM wrapper. The wrapper isolates the global styles and injects the theme variables (`--ab-color-primary`, `--ab-color-surface`, `--ab-color-text`, `--ab-radius-sm`, `--ab-font-mono` and others; see `tokens.css` of `@autobangumi/plugin-ui` for the full list). A component without a build step can use `var(--ab-…)` directly. Light and dark mode switch automatically.

## Build template

If you do not want to write a native module by hand, use the workspace package `@autobangumi/plugin-ui` (`webui/packages/plugin-ui/`; it is not published to npm):

- `src/index.ts`: the types `AbHost`, `AbPluginElement`, `AbSlotContext` and more.
- `tokens.css`: the theme variables.
- `template/`: a Vite library-mode template. It writes one self-contained ES module to `../web/index.js` and inlines `tokens.css` into the Shadow DOM. Copy it into your plugin and change the element name.

## Limits

- **CSP**: AB pages have `Content-Security-Policy: script-src 'self'`. The module must come from an AB address (`/api/v1/plugins/<id>/web/...`). Inline scripts, `eval` and scripts from third-party CDNs are not allowed. Images, styles and network requests are not limited.
- **Static files**: the `web/` directory is served at `GET /api/v1/plugins/<id>/web/<path>`. It needs a login, serves enabled plugins only and refuses paths and symlinks that leave the directory. For this reason, the `api_router` of a plugin cannot use the prefix `web/`.
- **Error boundary**: a failed module import, an undefined element, or an uncaught error in a component makes only the slots of that plugin show "plugin component failed to load". The page and other plugins are not affected. There is no retry button. Reload the page to import again.
- **Cache**: the module has `Cache-Control: no-cache`. After a plugin upgrade, the browser re-validates with the ETag.

A complete working example is `examples/plugins/manual-pick/`. It is a tab on the detail page. It lists torrents through the read-only host API, saves the choice through a route of the plugin, and refreshes with `host.events.on` when a pick is made elsewhere.
