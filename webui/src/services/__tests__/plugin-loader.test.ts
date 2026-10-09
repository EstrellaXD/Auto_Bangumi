import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import type { PluginUiSlot } from '@autobangumi/plugin-ui';
import {
  loadPluginElement,
  moduleUrl,
  watchPluginErrors,
} from '../plugin-loader';

// happy-dom 默认的 about:blank 不能作为 URL 的 base
beforeAll(() => {
  (window as any).happyDOM.setURL('http://ab.local/');
});

let counter = 0;

/** 每个用例用独立的插件 id，避免模块缓存互相影响 */
function makeSlot(): PluginUiSlot {
  counter += 1;
  return {
    plugin_id: `demo${counter}`,
    slot: 'bangumi.detail.tab',
    element: `ab-plugin-demo${counter}`,
    entry: 'web/index.js',
    title: { 'zh-CN': '演示' },
  };
}

function define(name: string) {
  customElements.define(name, class extends HTMLElement {});
}

describe('moduleUrl', () => {
  it('should point at the plugin web route with an absolute URL', () => {
    const url = moduleUrl({ plugin_id: 'my plugin', entry: 'web/index.js' });
    expect(url).toMatch(/^[a-z]+:/);
    expect(url).toContain('/api/v1/plugins/my%20plugin/web/index.js');
  });
});

describe('loadPluginElement', () => {
  it('should import a module once for repeated mounts', async () => {
    const slot = makeSlot();
    const importer = vi.fn(async () => define(slot.element));

    await loadPluginElement(slot, importer);
    await loadPluginElement(slot, importer);

    expect(importer).toHaveBeenCalledTimes(1);
    expect(importer).toHaveBeenCalledWith(moduleUrl(slot));
  });

  it('should reject when the module does not define the element', async () => {
    const slot = makeSlot();
    await expect(loadPluginElement(slot, async () => {})).rejects.toThrow(
      /not defined/
    );
  });

  it('should retry after a failed import', async () => {
    const slot = makeSlot();
    const importer = vi
      .fn()
      .mockRejectedValueOnce(new Error('404'))
      .mockImplementationOnce(async () => define(slot.element));

    await expect(loadPluginElement(slot, importer)).rejects.toThrow('404');
    await loadPluginElement(slot, importer);

    expect(importer).toHaveBeenCalledTimes(2);
  });
});

/** 让 define 调用的调用栈带上插件脚本地址，模拟插件模块顶层代码 */
function defineFrom(pluginId: string, name: string, guarded = false) {
  const body = `
    if (!${guarded} || !customElements.get(name)) {
      customElements.define(name, class extends HTMLElement {});
    }
    //# sourceURL=http://ab.local/api/v1/plugins/${pluginId}/web/index.js`;
  // eslint-disable-next-line no-new-func
  new Function('name', body)(name);
}

describe('element ownership', () => {
  it('should reject an element that another plugin defined first', async () => {
    const slot = makeSlot();
    // 别的插件抢先定义了本插件声明的元素名，本插件自己的 define 被守卫跳过
    const importer = async () => {
      defineFrom('squatter', slot.element);
      defineFrom(slot.plugin_id, slot.element, true);
    };

    await expect(loadPluginElement(slot, importer)).rejects.toThrow(
      /defined by plugin squatter/
    );
  });

  it('should accept an element that the plugin defined itself', async () => {
    const slot = makeSlot();
    await loadPluginElement(slot, async () =>
      defineFrom(slot.plugin_id, slot.element)
    );
  });
});

describe('watchPluginErrors', () => {
  const stops: Array<() => void> = [];
  afterEach(() => stops.splice(0).forEach((stop) => stop()));

  function fire(filename: string) {
    window.dispatchEvent(
      new ErrorEvent('error', { filename, error: new Error('boom') })
    );
  }

  it('should report errors from that plugin script only', () => {
    const mine = vi.fn();
    const others = vi.fn();
    stops.push(watchPluginErrors('demo', mine), watchPluginErrors('x', others));

    fire('http://ab.local/api/v1/plugins/demo/web/index.js');

    expect(mine).toHaveBeenCalledTimes(1);
    expect(others).not.toHaveBeenCalled();
  });

  it('should ignore errors from host scripts', () => {
    const mine = vi.fn();
    stops.push(watchPluginErrors('demo', mine));

    fire('http://ab.local/assets/index-abc.js');

    expect(mine).not.toHaveBeenCalled();
  });

  it('should stop reporting after unsubscribing', () => {
    const mine = vi.fn();
    watchPluginErrors('demo', mine)();

    fire('http://ab.local/api/v1/plugins/demo/web/index.js');

    expect(mine).not.toHaveBeenCalled();
  });
});
