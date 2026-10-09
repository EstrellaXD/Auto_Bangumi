import { flushPromises, mount } from '@vue/test-utils';
import ConfigPlugins from '../config-plugins.vue';
import type { PluginInfo, PluginsOverview } from '#/plugins';
import en from '@/i18n/en.json';
import zhCN from '@/i18n/zh-CN.json';
import { apiPlugins } from '@/api/plugins';

vi.mock('@/api/plugins', () => ({
  apiPlugins: {
    list: vi.fn(),
    update: vi.fn(),
    updateSettings: vi.fn(),
    uninstall: vi.fn(),
  },
}));

const pushMock = vi.fn();
vi.stubGlobal('useRouter', () => ({ push: pushMock }));

const confirmMock = vi.fn();
vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: confirmMock }),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));
vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ success: vi.fn(), error: vi.fn() }),
}));
vi.mock('@/hooks/usePluginProviders', () => ({
  refreshPluginProviders: vi.fn(),
}));
vi.mock('@/hooks/usePluginUi', () => ({ refreshPluginUi: vi.fn() }));
const refreshGroupMock = vi.fn();
const storeConfig = {
  plugins: {
    instances: [
      { id: 'main', point: 'downloader', provider: 'qbittorrent', options: {} },
      { id: 'box', point: 'downloader', provider: 'tr', options: {} },
    ],
    slots: { rename_strategy: 'pn' },
  },
  notification: { providers: [{ type: 'ntfy', enabled: true }] },
};
vi.mock('@/store/config', () => ({
  useConfigStore: () => ({
    refreshGroup: refreshGroupMock,
    config: storeConfig,
  }),
}));

const api = vi.mocked(apiPlugins);

function plugin(overrides: Partial<PluginInfo> = {}): PluginInfo {
  return {
    id: 'ntfy',
    name: 'ntfy',
    version: '0.1.0',
    source: 'catalog',
    signed: true,
    state: 'active',
    enabled: true,
    description: '',
    permissions: [],
    error: null,
    config_schema: null,
    options: {},
    providers: {},
    ...overrides,
  };
}

function overview(plugins: PluginInfo[]): PluginsOverview {
  return { allow_unsigned: false, plugins };
}

async function mountPage(plugins: PluginInfo[]) {
  api.list.mockResolvedValue(overview(plugins));
  const wrapper = mount(ConfigPlugins, {
    global: {
      stubs: {
        'ab-fold-panel': { template: '<section><slot /></section>' },
        AbSwitch: true,
      },
    },
  });
  await flushPromises();
  return wrapper;
}

function button(wrapper: Awaited<ReturnType<typeof mountPage>>, key: string) {
  return wrapper.findAll('button').filter((b) => b.text() === key);
}

const sources: PluginInfo['source'][] = ['builtin', 'catalog', 'local', 'pip'];

describe('config-plugins', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each(sources)(
    'should have a source label in both locales when source is %s',
    (source) => {
      const key = `source_${source}`;
      expect(en.config.plugins_set).toHaveProperty(key);
      expect(zhCN.config.plugins_set).toHaveProperty(key);
    }
  );

  it.each(sources)(
    'should offer uninstall only for catalog plugins when source is %s',
    async (source) => {
      const wrapper = await mountPage([plugin({ source })]);
      expect(button(wrapper, 'config.plugins_set.uninstall')).toHaveLength(
        source === 'catalog' ? 1 : 0
      );
    }
  );

  it.each([true, false])(
    'should uninstall only when the confirm resolves %s',
    async (confirmed) => {
      confirmMock.mockResolvedValue(confirmed);
      api.uninstall.mockResolvedValue(overview([]));
      const wrapper = await mountPage([plugin()]);

      await button(wrapper, 'config.plugins_set.uninstall')[0].trigger('click');
      await flushPromises();

      expect(confirmMock).toHaveBeenCalledWith(
        expect.objectContaining({ danger: true })
      );
      expect(api.uninstall).toHaveBeenCalledTimes(confirmed ? 1 : 0);
      expect(wrapper.text().includes('config.plugins_set.empty')).toBe(
        confirmed
      );
    }
  );

  it('should link to the plugin market instead of listing the catalog', async () => {
    const wrapper = await mountPage([]);

    await button(wrapper, 'config.plugins_set.open_market')[0].trigger('click');

    expect(pushMock).toHaveBeenCalledWith('/market');
  });

  it('should refresh allow_unsigned in the config store when the card toggles it', async () => {
    api.updateSettings.mockResolvedValue({ allow_unsigned: true, plugins: [] });
    const wrapper = await mountPage([]);

    wrapper
      .findAllComponents({ name: 'AbSwitch' })[0]
      .vm.$emit('update:model-value', true);
    await flushPromises();

    expect(api.updateSettings).toHaveBeenCalledWith(true);
    expect(refreshGroupMock).toHaveBeenCalledWith(
      'plugins',
      expect.arrayContaining(['allow_unsigned'])
    );
  });

  it('should keep unsaved edits of other plugins when one plugin is toggled', async () => {
    const schema = { properties: { url: { type: 'string' as const } } };
    const a = plugin({
      id: 'a',
      config_schema: schema,
      options: { url: 'old' },
    });
    const b = plugin({ id: 'b', config_schema: schema, enabled: false });
    api.update.mockResolvedValue(overview([a, { ...b, enabled: true }]));
    const wrapper = await mountPage([a, b]);

    await wrapper.find('input').setValue('typed');
    // 第 0 个开关是 allow_unsigned，之后依次是插件 a、b
    wrapper
      .findAllComponents({ name: 'AbSwitch' })[2]
      .vm.$emit('update:model-value', true);
    await flushPromises();

    expect(api.update).toHaveBeenCalledWith('b', { enabled: true });
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      'typed'
    );
  });
});

describe('config-plugins states', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show an error with retry when the initial load fails', async () => {
    api.list.mockRejectedValueOnce(new Error('x'));
    const wrapper = mount(ConfigPlugins, {
      global: {
        stubs: {
          'ab-fold-panel': { template: '<section><slot /></section>' },
          AbSwitch: true,
        },
      },
    });
    await flushPromises();
    expect(wrapper.text()).toContain('config.plugins_set.retry');

    api.list.mockResolvedValue(overview([plugin({ name: 'recovered' })]));
    await button(wrapper as never, 'config.plugins_set.retry')[0].trigger(
      'click'
    );
    await flushPromises();
    expect(wrapper.text()).toContain('recovered');
  });

  it('should name each enable switch after its plugin', async () => {
    const wrapper = await mountPage([plugin({ name: 'ntfy' })]);
    expect(
      wrapper.findAllComponents({ name: 'AbSwitch' })[1].props('ariaLabel')
    ).toBe('config.plugins_set.enabled_for');
  });

  it('should enable Save and show an unsaved marker only after an edit', async () => {
    const wrapper = await mountPage([
      plugin({
        config_schema: { properties: { url: { type: 'string', default: '' } } },
        options: { url: 'a' },
      }),
    ]);
    const save = () => button(wrapper, 'config.plugins_set.save')[0];
    expect(save().attributes('disabled')).toBeDefined();
    expect(wrapper.text()).not.toContain('config.plugins_set.unsaved');

    await wrapper.find('input').setValue('b');
    expect(save().attributes('disabled')).toBeUndefined();
    expect(wrapper.text()).toContain('config.plugins_set.unsaved');
  });
});

describe('config-plugins impact warning', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.update.mockResolvedValue(overview([]));
  });

  function toggleOff(wrapper: Awaited<ReturnType<typeof mountPage>>) {
    // 第 0 个开关是 allow_unsigned
    wrapper
      .findAllComponents({ name: 'AbSwitch' })[1]
      .vm.$emit('update:model-value', false);
    return flushPromises();
  }

  it.each([
    // [插件 Provider, 确认结果, 是否询问, 是否停用]
    [{}, undefined, false, true],
    [{ downloader: ['aria2'] }, undefined, false, true],
    [{ downloader: ['tr'] }, false, true, false],
    [{ downloader: ['tr'] }, true, true, true],
    [{ notifier: ['ntfy'] }, true, true, true],
    [{ rename_strategy: ['pn', 'advance'] }, false, true, false],
  ])(
    'should confirm disabling when providers %j are in use (confirm=%s)',
    async (providers, confirmed, asked, disabled) => {
      confirmMock.mockResolvedValue(confirmed);
      const wrapper = await mountPage([plugin({ providers })]);

      await toggleOff(wrapper);

      expect(confirmMock).toHaveBeenCalledTimes(asked ? 1 : 0);
      if (asked)
        expect(confirmMock).toHaveBeenCalledWith(
          expect.objectContaining({
            danger: true,
            body: 'config.plugins_set.in_use',
          })
        );
      expect(api.update).toHaveBeenCalledTimes(disabled ? 1 : 0);
    }
  );

  it('should name the affected settings in the uninstall confirm', async () => {
    confirmMock.mockResolvedValue(false);
    const wrapper = await mountPage([
      plugin({ providers: { downloader: ['tr'] } }),
    ]);

    await button(wrapper, 'config.plugins_set.uninstall')[0].trigger('click');
    await flushPromises();

    expect(confirmMock.mock.calls[0][0].body).toBe(
      'config.plugins_set.in_use config.plugins_set.uninstall_confirm_body'
    );
  });
});
