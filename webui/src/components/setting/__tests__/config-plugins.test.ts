import { flushPromises, mount } from '@vue/test-utils';
import ConfigPlugins from '../config-plugins.vue';
import type { CatalogEntry, PluginInfo, PluginsOverview } from '#/plugins';
import en from '@/i18n/en.json';
import zhCN from '@/i18n/zh-CN.json';
import { apiPlugins } from '@/api/plugins';

vi.mock('@/api/plugins', () => ({
  apiPlugins: {
    list: vi.fn(),
    update: vi.fn(),
    updateSettings: vi.fn(),
    catalog: vi.fn(),
    install: vi.fn(),
    uninstall: vi.fn(),
  },
}));

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
vi.mock('@/store/config', () => ({
  useConfigStore: () => ({ refreshGroup: refreshGroupMock }),
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
    ...overrides,
  };
}

function overview(plugins: PluginInfo[]): PluginsOverview {
  return { allow_unsigned: false, plugins };
}

function entry(overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: 'ntfy',
    name: 'ntfy',
    version: '0.2.0',
    kind: 'plugin',
    extension_points: ['notifier'],
    description: '',
    min_ab_version: '4.0.0',
    installed_version: null,
    ...overrides,
  };
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

  it('should load the catalog only when the user browses it', async () => {
    api.catalog.mockResolvedValue([]);
    const wrapper = await mountPage([]);
    expect(api.catalog).not.toHaveBeenCalled();

    await button(wrapper, 'config.plugins_set.catalog_browse')[0].trigger(
      'click'
    );
    await flushPromises();

    expect(api.catalog).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain('config.plugins_set.catalog_empty');
  });

  it('should show the install action for each catalog state', async () => {
    api.catalog.mockResolvedValue([
      entry({ id: 'fresh' }),
      entry({ id: 'stale', installed_version: '0.1.0' }),
      entry({ id: 'current', installed_version: '0.2.0' }),
    ]);
    const wrapper = await mountPage([]);
    await button(wrapper, 'config.plugins_set.catalog_browse')[0].trigger(
      'click'
    );
    await flushPromises();

    const rows = wrapper.findAll('.catalog__entry');
    expect(rows.map((r) => r.find('button').exists())).toEqual([
      true,
      true,
      false,
    ]);
    expect(rows[0].find('button').text()).toBe('config.plugins_set.install');
    expect(rows[1].find('button').text()).toBe('config.plugins_set.update');
    expect(rows[2].text()).toContain('config.plugins_set.installed');
  });

  it('should install, apply the returned overview and mark the entry installed', async () => {
    api.catalog.mockResolvedValue([entry()]);
    api.install.mockResolvedValue(
      overview([plugin({ name: 'ntfy-installed', version: '0.2.0' })])
    );
    const wrapper = await mountPage([]);
    await button(wrapper, 'config.plugins_set.catalog_browse')[0].trigger(
      'click'
    );
    await flushPromises();

    await button(wrapper, 'config.plugins_set.install')[0].trigger('click');
    await flushPromises();

    expect(api.install).toHaveBeenCalledWith('ntfy');
    expect(wrapper.text()).toContain('ntfy-installed');
    expect(button(wrapper, 'config.plugins_set.install')).toHaveLength(0);
    expect(wrapper.find('.catalog__entry').text()).toContain(
      'config.plugins_set.installed'
    );
  });

  it('should keep the entry installable when install fails', async () => {
    api.catalog.mockResolvedValue([entry()]);
    api.install.mockRejectedValue(new Error('signature invalid'));
    const wrapper = await mountPage([]);
    await button(wrapper, 'config.plugins_set.catalog_browse')[0].trigger(
      'click'
    );
    await flushPromises();

    await button(wrapper, 'config.plugins_set.install')[0].trigger('click');
    await flushPromises();

    expect(button(wrapper, 'config.plugins_set.install')).toHaveLength(1);
  });

  it('should show the backend detail inline when the catalog is unavailable', async () => {
    api.catalog.mockRejectedValue({
      response: { data: { detail: 'catalog signature verification failed' } },
    });
    const wrapper = await mountPage([]);
    await button(wrapper, 'config.plugins_set.catalog_browse')[0].trigger(
      'click'
    );
    await flushPromises();

    const alert = wrapper.find('[role="alert"]');
    expect(alert.text()).toContain('config.plugins_set.catalog_failed');
    expect(alert.text()).toContain('catalog signature verification failed');
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
