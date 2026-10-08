import { mount } from '@vue/test-utils';
import { defineComponent, nextTick, ref } from 'vue';
import ConfigDownload from '../config-download.vue';
import type { Plugins } from '#/config';

vi.mock('@/hooks/usePluginProviders', () => ({
  usePluginProviders: () =>
    ref({
      downloader: ['transmission'],
      notifier: [],
      search_site: [],
      metadata_provider: [],
      rename_strategy: [],
    }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: () => Promise.resolve(true) }),
}));

function instance(id: string) {
  return {
    id,
    point: 'downloader',
    provider: 'qbittorrent',
    options: {
      host: `${id}:8080`,
      username: '',
      password: '',
      path: '',
      ssl: false,
    },
  };
}

const state = ref({} as Plugins);

vi.mock('@/store/config', () => ({
  useConfigStore: () => ({ getSettingGroup: () => state }),
}));

const AbSettingStub = defineComponent({
  name: 'AbSettingStub',
  props: {
    data: { type: [String, Boolean], default: undefined },
    label: { type: [String, Function], required: true },
    prop: { type: Object, default: undefined },
    type: { type: String, required: true },
  },
  emits: ['update:data'],
  template: '<div class="setting-stub"></div>',
});

function mountIt() {
  return mount(ConfigDownload, {
    global: {
      stubs: {
        'ab-fold-panel': { template: '<section><slot /></section>' },
        'ab-setting': AbSettingStub,
        'ab-button': {
          emits: ['click'],
          template: '<button @click="$emit(\'click\')"><slot /></button>',
        },
        'ab-input': {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
      },
    },
  });
}

function rows(wrapper: ReturnType<typeof mountIt>) {
  return wrapper
    .findAll('[data-instance]')
    .map((r) => r.attributes('data-instance'));
}

describe('config-download', () => {
  beforeEach(() => {
    state.value = {
      slots: { downloader: 'default' },
      instances: [instance('default'), instance('nas')],
    } as unknown as Plugins;
  });

  it('should list every downloader instance and mark the default', () => {
    const wrapper = mountIt();
    expect(rows(wrapper)).toEqual(['default', 'nas']);
    expect(wrapper.find('[data-instance="default"]').text()).toContain(
      'config.downloader_set.default'
    );
  });

  it('should offer plugin downloaders in the provider dropdown', () => {
    const wrapper = mountIt();
    const type = wrapper
      .findAllComponents(AbSettingStub)
      .find(
        (s) =>
          (s.props('label') as () => string)() === 'config.downloader_set.type'
      );
    expect(type?.props('prop')?.items).toEqual([
      'qbittorrent',
      'aria2',
      'transmission',
    ]);
  });

  it('should add an instance with a new id and edit it', async () => {
    const wrapper = mountIt();
    await wrapper.find('[data-new-instance] input').setValue('seedbox');
    await wrapper.find('[data-action="add"]').trigger('click');
    expect(rows(wrapper)).toEqual(['default', 'nas', 'seedbox']);
    expect(state.value.instances[2].point).toBe('downloader');
    expect(wrapper.find('[data-instance="seedbox"]').classes()).toContain(
      'is-editing'
    );
  });

  it('should not add an instance whose id already exists', async () => {
    const wrapper = mountIt();
    await wrapper.find('[data-new-instance] input').setValue('nas');
    await wrapper.find('[data-action="add"]').trigger('click');
    expect(rows(wrapper)).toEqual(['default', 'nas']);
  });

  it('should set another instance as the default', async () => {
    const wrapper = mountIt();
    await wrapper
      .find('[data-instance="nas"] [data-action="set-default"]')
      .trigger('click');
    expect(state.value.slots.downloader).toBe('nas');
  });

  it('should delete a non-default instance but offer no delete for the default', async () => {
    const wrapper = mountIt();
    expect(
      wrapper.find('[data-instance="default"] [data-action="delete"]').exists()
    ).toBe(false);
    await wrapper
      .find('[data-instance="nas"] [data-action="delete"]')
      .trigger('click');
    await nextTick();
    await nextTick();
    expect(rows(wrapper)).toEqual(['default']);
  });
});
