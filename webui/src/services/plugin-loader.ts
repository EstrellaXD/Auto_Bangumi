import type { PluginUiSlot } from '@autobangumi/plugin-ui';

type Importer = (url: string) => Promise<unknown>;

const loading = new Map<string, Promise<unknown>>();

// import() 的相对地址按「当前脚本」解析，所以这里先按文档解析成绝对地址
export function moduleUrl(ui: Pick<PluginUiSlot, 'plugin_id' | 'entry'>) {
  return new URL(
    `api/v1/plugins/${encodeURIComponent(ui.plugin_id)}/${ui.entry}`,
    document.baseURI
  ).href;
}

// custom element 名是文档全局的。记录每个名字由哪个插件的脚本定义，
// 挂载点只接受本插件自己定义的元素，其它插件抢先定义（或守卫跳过）的不用。
const owners = new Map<string, string>();
const PLUGIN_FRAME = /\/plugins\/([^/]+)\/web\//;
let tracking = false;

// 须在任何插件代码运行前安装；按调用栈里最近的插件脚本地址判定定义者
function trackDefinitions() {
  if (tracking) return;
  tracking = true;
  const define = customElements.define.bind(customElements);
  customElements.define = (name, ctor, options) => {
    define(name, ctor, options);
    const frame = new Error(name).stack?.match(PLUGIN_FRAME);
    if (frame) owners.set(name, decodeURIComponent(frame[1]));
  };
}

/**
 * 导入挂载点所在的模块并确认 custom element 已定义。同一模块只导入一次，
 * 失败不缓存（插件修复后重新打开页面即可重试）。
 */
export async function loadPluginElement(
  ui: PluginUiSlot,
  importer: Importer = (url) => import(/* @vite-ignore */ url)
): Promise<void> {
  trackDefinitions();
  const url = moduleUrl(ui);
  let pending = loading.get(url);
  if (!pending) {
    pending = importer(url);
    loading.set(url, pending);
    pending.catch(() => loading.delete(url));
  }
  await pending;
  const owner = owners.get(ui.element);
  if (owner && owner !== ui.plugin_id) {
    throw new Error(
      `custom element <${ui.element}> is defined by plugin ${owner}`
    );
  }
  if (!customElements.get(ui.element)) {
    throw new Error(`custom element <${ui.element}> is not defined`);
  }
}

type ErrorListener = (error: unknown) => void;

const errorListeners = new Map<string, Set<ErrorListener>>();

function blame(source: unknown, error: unknown) {
  if (typeof source !== 'string') return;
  for (const [pluginId, listeners] of errorListeners) {
    if (source.includes(`/plugins/${encodeURIComponent(pluginId)}/web/`)) {
      listeners.forEach((listener) => listener(error));
    }
  }
}

function onWindowError(event: ErrorEvent) {
  blame(event.filename || event.error?.stack, event.error ?? event.message);
}

function onRejection(event: PromiseRejectionEvent) {
  blame(event.reason?.stack, event.reason);
}

/**
 * 插件组件在 custom element 回调、事件处理函数或 Promise 里抛出的错误不会
 * 经过 append 传回宿主，只会成为 window 上的 error / unhandledrejection。
 * 这里按脚本地址（``/plugins/<id>/web/``）把它们归给对应插件。
 * 返回取消监听函数。
 */
export function watchPluginErrors(
  pluginId: string,
  listener: ErrorListener
): () => void {
  if (errorListeners.size === 0) {
    window.addEventListener('error', onWindowError);
    window.addEventListener('unhandledrejection', onRejection);
  }
  const listeners = errorListeners.get(pluginId) ?? new Set();
  listeners.add(listener);
  errorListeners.set(pluginId, listeners);

  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) errorListeners.delete(pluginId);
    if (errorListeners.size === 0) {
      window.removeEventListener('error', onWindowError);
      window.removeEventListener('unhandledrejection', onRejection);
    }
  };
}
