# 前端挂载点

插件可以在 WebUI 的固定位置挂载自己的界面。界面是标准的 Web Component（custom element）：一个 ES module 定义元素，AB 创建它并传入 `host` 与 `context`。不依赖任何前端框架；想用 Vue、Lit 等，自己打包进模块即可。

## 清单

```toml
[[plugin.ui]]
slot = "bangumi.detail.tab"
element = "ab-plugin-manual-pick"
entry = "web/index.js"
title = { zh-CN = "手动选种", en-US = "Manual pick" }
```

- `slot`：挂载点，见下表。
- `element`：custom element 名。必须是 `ab-plugin-<插件 id>`，或以 `ab-plugin-<插件 id>-` 开头。命名空间归插件所有，插件不能定义别人的元素名。
- `entry`：定义该元素的 ES module，位于 `web/` 下。
- `title`：按语言的标题，至少一种语言。用作标签页、页面标题或设置分区名。

清单不合法时整个插件被拒绝加载。`ab-plugin validate` 会检查入口文件是否存在。

## 挂载点

| `slot` | 位置 | `context` |
| --- | --- | --- |
| `settings.section` | 设置页分区列表末尾，侧栏与搜索可见 | `{}` |
| `bangumi.detail.tab` | 番剧编辑弹窗里多一个标签（有插件标签时才显示分段控件） | `{ bangumiId }` |
| `bangumi.card.action` | 番剧卡片标题下的操作条 | `{ bangumiId }` |
| `page` | 侧边栏多一个入口，路由 `/plugins/<id>`；页面标题取清单标题 | `{}` |
| `dashboard.widget` | 番剧列表页顶部的网格 | `{}` |

移动端底部导航没有插件页入口，手机上只能直接访问地址。

## 组件与 AbHost

AB 先设置 `host` 和 `context` 属性，再把元素插入文档，所以 `connectedCallback` 里可以直接使用它们。

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

| 成员 | 说明 |
| --- | --- |
| `host.pluginId` | 插件 id |
| `host.api.get/post/put/delete` | 带登录态的请求，返回已解析的 JSON，非 2xx 时 reject。不以 `/` 开头的路径相对 `/api/v1/plugins/<id>/`；以 `/api/v1/` 开头的宿主 API 只允许 GET（公开只读，含其它插件的 GET 路由） |
| `host.i18n.locale` | 当前语言，如 `zh-CN`、`en-US` |
| `host.i18n.t(key, params?)` | 翻译宿主文案；找不到时返回 key |
| `host.theme.mode` / `host.theme.tokens` | 深浅色与 `--ab-*` 变量的当前值，随主题实时变化 |
| `host.toast(message, kind?)` | 弹出提示（`info` 或 `error`） |
| `host.events.on(kind, callback)` | 订阅事件总线上的事件，回调收到事件字段；返回取消订阅函数。组件卸载时 AB 也会取消 |

路径越界（`..`、`//host`、完整 URL）会被拒绝。这是防误用的边界，不是安全边界：组件与主站同源，等同于插件拥有完整权限。请求默认不弹错误提示，由插件自己决定如何展示。

## 样式

AB 把组件放进 Shadow DOM 包裹层隔离全局样式，并注入主题变量（`--ab-color-primary`、`--ab-color-surface`、`--ab-color-text`、`--ab-radius-sm`、`--ab-font-mono` 等，完整列表见 `@autobangumi/plugin-ui` 的 `tokens.css`）。不做构建的组件直接用 `var(--ab-…)`。深浅色自动切换。

## 构建模板

不想手写原生模块时，用工作区包 `@autobangumi/plugin-ui`（`webui/packages/plugin-ui/`，不发布到 npm）：

- `src/index.ts`：`AbHost`、`AbPluginElement`、`AbSlotContext` 等类型。
- `tokens.css`：主题变量。
- `template/`：Vite 库模式模板，输出单文件自包含 ES module 到 `../web/index.js`，把 `tokens.css` 内联进 Shadow DOM。把它复制到你的插件里，改元素名即可。

## 约束

- **CSP**：AB 的页面带 `Content-Security-Policy: script-src 'self'`。模块必须来自 AB 自己的地址（`/api/v1/plugins/<id>/web/...`）；不能用内联脚本、`eval` 或第三方 CDN 的脚本。图片、样式和网络请求不受限。
- **静态资源**：`web/` 目录由 `GET /api/v1/plugins/<id>/web/<路径>` 提供，要求登录，只服务已启用的插件，拒绝目录外的路径和符号链接。因此插件的 `api_router` 不能使用 `web/` 前缀。
- **错误边界**：模块导入失败、元素未定义、组件里抛出的未捕获错误，都只让该插件的挂载点显示「插件组件加载失败」，页面与其它插件不受影响。没有重试按钮，重新打开页面会重新导入。
- **缓存**：模块带 `Cache-Control: no-cache`，升级插件后按 ETag 重新验证。

完整的可运行例子是 `examples/plugins/manual-pick/`：详情页标签，经宿主只读 API 列出种子，经插件自己的路由保存选择，并用 `host.events.on` 在别处选种后刷新。
