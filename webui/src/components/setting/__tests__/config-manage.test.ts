import { mount } from '@vue/test-utils';
import { defineComponent, nextTick } from 'vue';
import ConfigManage from '../config-manage.vue';

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('@/store/config', async () => {
  const { computed } = await vi.importActual<typeof import('vue')>('vue');
  const manageState = {
    enable: true,
    eps_complete: false,
    rename_method: 'pn',
    revision_conflict_policy: 'hold',
    group_tag: false,
    remove_bad_torrent: false,
    track_orphans: true,
  };
  return {
    __manageState: manageState,
    useConfigStore: () => ({
      getSettingGroup: () => computed(() => manageState),
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
      __manageState: { revision_conflict_policy: string };
    };
    expect(store.__manageState.revision_conflict_policy).toBe('replace');
  });
});
