import { mount } from '@vue/test-utils';
import { defineComponent, nextTick } from 'vue';
import ConfigParser from '../config-parser.vue';

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('@/store/config', async () => {
  const { computed } = await vi.importActual<typeof import('vue')>('vue');
  const parserState = {
    enable: true,
    engine: 'classic',
    filter: [] as string[],
    language: 'zh',
  };
  return {
    __parserState: parserState,
    useConfigStore: () => ({
      getSettingGroup: () => computed(() => parserState),
    }),
  };
});

const AbSettingStub = defineComponent({
  name: 'AbSettingStub',
  props: {
    data: { type: [String, Boolean, Array], default: undefined },
    description: { type: String, default: '' },
    label: { type: [String, Function], required: true },
    prop: { type: Object, default: undefined },
    type: { type: String, required: true },
  },
  emits: ['update:data'],
  template: '<div class="setting-stub"></div>',
});

describe('config-parser', () => {
  it('shows both parser engines and defaults to Classic', async () => {
    const wrapper = mount(ConfigParser, {
      global: {
        stubs: {
          'ab-fold-panel': { template: '<section><slot /></section>' },
          'ab-setting': AbSettingStub,
        },
      },
    });
    const settings = wrapper.findAllComponents(AbSettingStub);
    const engine = settings.find((setting) => {
      const label = setting.props('label') as () => string;
      return label() === 'config.parser_set.engine';
    });

    expect(engine).toBeDefined();
    if (!engine) throw new Error('parser engine setting not found');
    expect(engine.props('data')).toBe('classic');
    expect(engine.props('description')).toBe('config.parser_set.engine_hint');
    expect(engine.props('prop')?.items).toEqual([
      {
        id: 1,
        label: 'config.parser_set.engine_classic',
        value: 'classic',
      },
      {
        id: 2,
        label: 'config.parser_set.engine_tokenizer',
        value: 'tokenizer',
      },
    ]);

    await engine.vm.$emit('update:data', 'tokenizer');
    await nextTick();
    const store = (await import('@/store/config')) as unknown as {
      __parserState: { engine: string };
    };
    expect(store.__parserState.engine).toBe('tokenizer');
  });
});
