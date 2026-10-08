import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import type { PluginUiSlot } from '@autobangumi/plugin-ui';
import AbAlert from '../basic/ab-alert.vue';
import PluginSlot from '../plugin-slot.vue';

const loadPluginElement = vi.fn();
const offBus = vi.fn();
const onBusEvent = vi.fn(() => offBus);

vi.mock('@/services/plugin-loader', async () => ({
  ...(await vi.importActual<object>('@/services/plugin-loader')),
  loadPluginElement: (...args: unknown[]) => loadPluginElement(...args),
}));
vi.mock('@/hooks/usePluginHostDeps', () => ({
  tokensCss: ':host{--ab-color-text:#000}',
  usePluginHostDeps: () => () => ({
    request: vi.fn(),
    locale: () => 'zh-CN',
    t: (key: string) => key,
    isDark: () => false,
    tokens: () => ({}),
    toast: vi.fn(),
    onBusEvent,
  }),
}));

// 记录 connectedCallback 触发时元素上已有的 host / context
const seen: Array<{ host: unknown; context: unknown }> = [];

let counter = 0;
function makeUi(plugin_id = 'demo'): PluginUiSlot {
  counter += 1;
  const element = `ab-plugin-slot-test-${counter}`;
  customElements.define(
    element,
    class extends HTMLElement {
      connectedCallback() {
        const el = this as unknown as Record<string, unknown>;
        seen.push({ host: el.host, context: el.context });
        this.textContent = 'plugin content';
      }
    }
  );
  return {
    plugin_id,
    slot: 'bangumi.detail.tab',
    element,
    entry: 'web/index.js',
    title: { 'zh-CN': '演示' },
  };
}

function mountSlot(ui: PluginUiSlot, context?: Record<string, unknown>) {
  return mount(PluginSlot, {
    props: { ui, context },
    global: { components: { AbAlert } },
    attachTo: document.body,
  });
}

function shadowText(w: ReturnType<typeof mountSlot>) {
  return w.find('.plugin-slot__body').element.shadowRoot?.textContent ?? '';
}

beforeAll(() => {
  (window as any).happyDOM.setURL('http://ab.local/');
});

afterEach(() => {
  loadPluginElement.mockReset();
  loadPluginElement.mockResolvedValue(undefined);
  seen.length = 0;
  vi.clearAllMocks();
});

describe('plugin-slot', () => {
  it('should mount the element in a shadow root with host and context set first', async () => {
    loadPluginElement.mockResolvedValue(undefined);
    const wrapper = mountSlot(makeUi(), { bangumiId: 3 });
    await flushPromises();

    expect(shadowText(wrapper)).toContain('plugin content');
    expect(seen).toHaveLength(1);
    expect(seen[0].context).toEqual({ bangumiId: 3 });
    expect((seen[0].host as { pluginId: string }).pluginId).toBe('demo');
    expect(wrapper.findComponent(AbAlert).exists()).toBe(false);
  });

  it('should show the failure notice when the module fails to load', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    loadPluginElement.mockRejectedValueOnce(new Error('404'));

    const broken = mountSlot(makeUi('broken'));
    const healthy = mountSlot(makeUi('healthy'));
    await flushPromises();

    const alert = broken.findComponent(AbAlert);
    expect(alert.props('title')).toBe('plugin.load_failed');
    expect(alert.text()).toContain('broken');
    // 其它挂载点不受影响
    expect(healthy.findComponent(AbAlert).exists()).toBe(false);
    expect(shadowText(healthy)).toContain('plugin content');
  });

  it('should replace the element with the failure notice on a runtime error from the plugin script', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const wrapper = mountSlot(makeUi('crashy'));
    await flushPromises();
    expect(wrapper.findComponent(AbAlert).exists()).toBe(false);

    window.dispatchEvent(
      new ErrorEvent('error', {
        filename: 'http://ab.local/api/v1/plugins/crashy/web/index.js',
        error: new Error('boom'),
      })
    );
    await flushPromises();

    expect(wrapper.findComponent(AbAlert).exists()).toBe(true);
    expect(shadowText(wrapper)).toBe('');
  });

  it('should rebuild the element when the context changes', async () => {
    const wrapper = mountSlot(makeUi(), { bangumiId: 1 });
    await flushPromises();

    await wrapper.setProps({ context: { bangumiId: 2 } });
    await flushPromises();

    expect(seen.map((s) => s.context)).toEqual([
      { bangumiId: 1 },
      { bangumiId: 2 },
    ]);
  });

  it('should release the plugin event subscriptions on unmount', async () => {
    const ui = makeUi();
    const wrapper = mountSlot(ui);
    await flushPromises();
    // 组件通过注入的 host 订阅事件
    const el = wrapper.find('.plugin-slot__body').element.shadowRoot!
      .firstElementChild!.nextElementSibling as unknown as {
      host: { events: { on: (kind: string, cb: () => void) => void } };
    };
    el.host.events.on('demo.event', () => {});

    wrapper.unmount();

    expect(offBus).toHaveBeenCalledTimes(1);
  });
});
