import { mount } from '@vue/test-utils';
import { defineComponent, nextTick, ref } from 'vue';
import ConfigManage from '../config-manage.vue';

vi.mock('@/hooks/usePluginProviders', () => ({
  usePluginProviders: () =>
    ref({
      downloader: [],
      notifier: [],
      search_site: [],
      metadata_provider: [],
      rename_strategy: ['advance', 'pn', 'template'],
    }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('@/store/config', async () => {
  const { computed } = await vi.importActual<typeof import('vue')>('vue');
  const manageState = {
    enable: true,
    eps_complete: false,
    group_tag: false,
    remove_bad_torrent: false,
    track_orphans: true,
  };
  const pluginsState = {
    slots: { rename_strategy: 'pn', conflict_policy: 'hold' },
  };
  return {
    __pluginsState: pluginsState,
    useConfigStore: () => ({
      getSettingGroup: (key: string) =>
        computed(() => (key === 'plugins' ? pluginsState : manageState)),
    }),
  };
});

const AbSettingStub = defineComponent({
  name: 'AbSettingStub',
  props: {
    data: { type: [String, Boolean], default: undefined },
    description: { type: String, default: '' },
    label: { type: [String, Function], required: true },
    prop: { type: Object, default: undefined },
    type: { type: String, required: true },
  },
  emits: ['update:data'],
  template: '<div class="setting-stub"></div>',
});

describe('config-manage', () => {
  it('offers a safe hold default and an explicit higher-revision replacement', async () => {
    const wrapper = mount(ConfigManage, {
      global: {
        stubs: {
          'ab-fold-panel': { template: '<section><slot /></section>' },
          'ab-setting': AbSettingStub,
        },
      },
    });
    const settings = wrapper.findAllComponents(AbSettingStub);
    const policy = settings.find((setting) => {
      const label = setting.props('label') as () => string;
      return label() === 'config.manage_set.revision_conflict_policy';
    });

    expect(policy).toBeDefined();
    if (!policy) throw new Error('revision conflict policy setting not found');
    expect(policy.props('data')).toBe('hold');
    expect(policy.props('description')).toBe(
      'config.manage_set.revision_conflict_hint'
    );
    expect(policy.props('prop')?.items).toEqual([
      {
        id: 1,
        label: 'config.manage_set.revision_conflict_hold',
        value: 'hold',
      },
      {
        id: 2,
        label: 'config.manage_set.revision_conflict_replace',
        value: 'replace',
      },
    ]);

    await policy.vm.$emit('update:data', 'replace');
    await nextTick();
    const store = (await import('@/store/config')) as unknown as {
      __pluginsState: { slots: { conflict_policy: string } };
    };
    expect(store.__pluginsState.slots.conflict_policy).toBe('replace');
  });

  it('should append plugin rename strategies when the rename plugin provides them', () => {
    const wrapper = mount(ConfigManage, {
      global: {
        stubs: {
          'ab-fold-panel': { template: '<section><slot /></section>' },
          'ab-setting': AbSettingStub,
        },
      },
    });
    const method = wrapper
      .findAllComponents(AbSettingStub)
      .find(
        (setting) =>
          (setting.props('label') as () => string)() ===
          'config.manage_set.method'
      );

    expect(method?.props('prop')?.items).toEqual([
      'pn',
      'advance',
      'none',
      'template',
    ]);
  });
});
