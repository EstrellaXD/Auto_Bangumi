import type { AbHost, AbHostApi } from '@autobangumi/plugin-ui';

type Method = 'get' | 'post' | 'put' | 'delete';

/** AbHost 依赖的宿主能力；测试里换成替身，运行时由 usePluginHostDeps 提供。 */
export interface HostDeps {
  request(
    method: Method,
    url: string,
    options: { params?: Record<string, unknown>; data?: unknown }
  ): Promise<unknown>;
  locale(): string;
  t(key: string, params?: Record<string, unknown>): string;
  isDark(): boolean;
  tokens(): Record<string, string>;
  toast(message: string, kind: 'info' | 'error'): void;
  /** 订阅事件总线（SSE `bus` 帧）上的 `kind`，回调收到事件负载 */
  onBusEvent(kind: string, callback: (payload: unknown) => void): () => void;
}

// 只用来借 URL 解析 ``..``、``%2e%2e``、``//host`` 等写法，不会发出请求
const ORIGIN = 'http://plugin.invalid';
const API_ROOT = '/api/v1/';

/**
 * 把组件传入的路径换成请求地址（相对文档，不带前导 ``/``，与其它 API 一致）。
 * 不以 ``/`` 开头的路径相对 ``/api/v1/plugins/<id>/``；``/api/v1/`` 开头的宿主
 * API 只允许 GET。越界（含 ``..``、其它来源）一律抛错。
 *
 * 这是防误用的边界，不是安全边界：组件与主站同源，等同于可以执行任意 JS。
 */
export function resolveApiUrl(
  pluginId: string,
  method: Method,
  path: string
): string {
  const prefix = `${API_ROOT}plugins/${encodeURIComponent(pluginId)}/`;
  const url = new URL(path, ORIGIN + prefix);
  const inside = url.origin === ORIGIN && url.pathname.startsWith(prefix);
  const publicRead =
    url.origin === ORIGIN &&
    method === 'get' &&
    url.pathname.startsWith(API_ROOT);
  if (!inside && !publicRead) {
    throw new Error(
      `plugin "${pluginId}" may not ${method.toUpperCase()} ${path}`
    );
  }
  return (url.pathname + url.search).slice(1);
}

/**
 * 构造注入给插件组件的 AbHost。返回的 dispose 取消该组件订阅的全部事件，
 * 在组件卸载时调用。
 */
export function createAbHost(
  pluginId: string,
  deps: HostDeps
): { host: AbHost; dispose: () => void } {
  const subscriptions = new Set<() => void>();

  const call = (
    method: Method,
    path: string,
    options: { params?: Record<string, unknown>; data?: unknown } = {}
  ) => {
    // 同步抛错也走 reject，调用方统一用 await / catch
    try {
      return deps.request(
        method,
        resolveApiUrl(pluginId, method, path),
        options
      );
    } catch (error) {
      return Promise.reject(error);
    }
  };

  const api: AbHostApi = {
    get: <T>(path: string, params?: Record<string, unknown>) =>
      call('get', path, { params }) as Promise<T>,
    post: <T>(path: string, body?: unknown) =>
      call('post', path, { data: body }) as Promise<T>,
    put: <T>(path: string, body?: unknown) =>
      call('put', path, { data: body }) as Promise<T>,
    delete: <T>(path: string) => call('delete', path) as Promise<T>,
  };

  const host: AbHost = {
    pluginId,
    api,
    i18n: {
      get locale() {
        return deps.locale();
      },
      t: (key, params) => deps.t(key, params),
    },
    theme: {
      // 随宿主深浅色切换，所以用 getter 而不是快照
      get mode() {
        return deps.isDark() ? 'dark' : 'light';
      },
      get tokens() {
        return deps.tokens();
      },
    },
    toast: (message, kind = 'info') => deps.toast(message, kind),
    events: {
      on(kind, callback) {
        const off = deps.onBusEvent(kind, callback);
        const unsubscribe = () => {
          off();
          subscriptions.delete(unsubscribe);
        };
        subscriptions.add(unsubscribe);
        return unsubscribe;
      },
    },
  };

  return {
    host,
    dispose: () => [...subscriptions].forEach((unsubscribe) => unsubscribe()),
  };
}
