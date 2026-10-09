/**
 * AutoBangumi 前端插件组件的宿主接口（设计文档第 3.8 节）。
 *
 * 插件在 `web/` 下提供 ES module，定义清单 `[[plugin.ui]]` 中声明的 custom
 * element。宿主创建元素后先设置 `host` 与 `context` 两个属性，再插入文档。
 * 组件只通过 `host` 与宿主交互，不直接使用宿主的 axios、store 或全局变量。
 *
 * 4.0 期间（ab_sdk 0.x）这些接口可能调整。
 */

/** 前端挂载点。 */
export type UiSlot =
  | 'settings.section'
  | 'bangumi.detail.tab'
  | 'bangumi.card.action'
  | 'page'
  | 'dashboard.widget';

/** `GET /api/v1/plugins/ui` 的一项：已启用插件声明的挂载点。 */
export interface PluginUiSlot {
  plugin_id: string;
  slot: UiSlot;
  /** custom element 名，以 `ab-plugin-` 开头 */
  element: string;
  /** 相对插件根目录（`web/...`），模块地址为 `/api/v1/plugins/<plugin_id>/<entry>` */
  entry: string;
  /** 按语言的标题，如 `{ 'zh-CN': '手动选种', 'en-US': 'Manual pick' }` */
  title: Record<string, string>;
}

/** 各挂载点传给组件的上下文。 */
export interface AbSlotContext {
  'settings.section': Record<string, never>;
  'bangumi.detail.tab': { bangumiId: number };
  'bangumi.card.action': { bangumiId: number };
  page: Record<string, never>;
  'dashboard.widget': Record<string, never>;
}

/**
 * 带登录态的请求。不以 `/` 开头的路径相对插件自己的路由前缀
 * `/api/v1/plugins/<pluginId>/`；以 `/api/v1/` 开头的宿主 API 只允许 GET。
 * 返回响应体（JSON 已解析），非 2xx 时 reject。
 */
export interface AbHostApi {
  get<T = unknown>(path: string, params?: Record<string, unknown>): Promise<T>;
  post<T = unknown>(path: string, body?: unknown): Promise<T>;
  put<T = unknown>(path: string, body?: unknown): Promise<T>;
  delete<T = unknown>(path: string): Promise<T>;
}

export interface AbHost {
  pluginId: string;
  api: AbHostApi;
  i18n: {
    /** 当前语言，如 `zh-CN`、`en-US` */
    locale: string;
    /** 宿主文案；找不到时返回 key 本身 */
    t(key: string, params?: Record<string, unknown>): string;
  };
  theme: {
    mode: 'light' | 'dark';
    /** `--ab-*` 变量的当前值（见 tokens.css） */
    tokens: Record<string, string>;
  };
  toast(message: string, kind?: 'info' | 'error'): void;
  events: {
    /**
     * 订阅宿主事件总线（SSE 的 `bus` 帧）上的事件 `kind`，回调收到事件的
     * 字段（dataclass 展开成对象，不含 `kind`）。返回取消订阅函数；组件
     * 卸载时宿主也会取消它的全部订阅。
     */
    on(kind: string, callback: (payload: unknown) => void): () => void;
  };
}

/** 插件元素在插入文档前由宿主设置的属性。 */
export interface AbPluginElement<S extends UiSlot = UiSlot>
  extends HTMLElement {
  host: AbHost;
  context: AbSlotContext[S];
}
