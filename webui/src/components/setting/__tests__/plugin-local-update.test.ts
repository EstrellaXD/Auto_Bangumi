import { flushPromises, mount } from '@vue/test-utils';
import PluginLocalUpdate from '../plugin-local-update.vue';
import PluginPipelines from '../plugin-pipelines.vue';
import type { PluginInfo } from '#/plugins';
import { apiPlugins } from '@/api/plugins';

vi.mock('@/api/plugins', () => ({
  apiPlugins: {
    localUpdate: vi.fn(),
    checkLocalUpdate: vi.fn(),
    installLocalUpdate: vi.fn(),
    localSource: vi.fn(),
    providers: vi.fn().mockResolvedValue({}),
    pipelines: vi.fn(),
  },
}));
vi.mock('@/hooks/usePluginRefresh', async () => {
  const { ref } = await import('vue');
  return { refreshPluginState: vi.fn(), pluginSetVersion: ref(0) };
});
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));
vi.mock('@/store/config', () => ({
  useConfigStore: () => ({
    config: {
      plugins: {
        slots: { organizer: 'missing/library', download_preflight: '' },
      },
    },
  }),
}));
const plugin: PluginInfo = {
  id: 'demo',
  name: 'Demo',
  version: '1.0.0',
  source: 'local',
  local_source: 'example/demo',
  signed: false,
  state: 'active',
  enabled: true,
  description: '',
  permissions: [],
  error: null,
  config_schema: null,
  options: {},
  providers: {},
};

it('checks again on update and installs the exact newly pinned version and token', async () => {
  vi.mocked(apiPlugins.localUpdate).mockResolvedValue({
    version: '2.0.0',
    available: true,
  });
  vi.mocked(apiPlugins.checkLocalUpdate).mockResolvedValue({
    plugin_id: 'demo',
    repository: 'example/demo',
    installed_version: '1.0.0',
    version: '2.1.0',
    available: true,
    release_url: '',
    notes: '',
    install_token: 'fresh-token',
  });
  vi.mocked(apiPlugins.installLocalUpdate).mockResolvedValue({
    allow_unsigned: true,
    plugins: [plugin],
  });
  const wrapper = mount(PluginLocalUpdate, {
    props: { plugin, allowUnsigned: true },
  });
  await flushPromises();
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'config.plugins_set.apply_update')!
    .trigger('click');
  await flushPromises();
  expect(apiPlugins.installLocalUpdate).toHaveBeenCalledWith(
    'demo',
    '2.1.0',
    'fresh-token'
  );
  expect(wrapper.emitted('updated')).toBeTruthy();
});

it('keeps a missing selected organizer visible without switching to native', async () => {
  const wrapper = mount(PluginPipelines);
  await flushPromises();
  const selects = wrapper.findAllComponents({ name: 'AbSelect' });
  expect(selects[0].props('options')).toContainEqual({
    value: 'missing/library',
    label: 'missing/library',
  });
  expect(selects[0].props('modelValue')).toBe('missing/library');
  expect(apiPlugins.pipelines).not.toHaveBeenCalled();
});
