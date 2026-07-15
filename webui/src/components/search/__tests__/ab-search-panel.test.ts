/* eslint-disable vue/one-component-per-file */
import { defineComponent, nextTick, ref } from 'vue';
import type { ComponentPublicInstance } from 'vue';
import { mount, shallowMount } from '@vue/test-utils';
import type { VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AbSearchPanel from '../ab-search-panel.vue';
import { useMessage } from '@/hooks/useMessage';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useBangumiStore } from '@/store/bangumi';
import { useSearchStore } from '@/store/search';

vi.mock('@/api/download', () => ({
  apiDownload: { subscribe: vi.fn() },
}));
vi.mock('@/hooks/useMessage', () => ({ useMessage: vi.fn() }));
vi.mock('@/hooks/useMyI18n', () => ({ useMyI18n: vi.fn() }));
vi.mock('@/store/bangumi', () => ({ useBangumiStore: vi.fn() }));
vi.mock('@/store/search', () => ({ useSearchStore: vi.fn() }));
vi.mock('@/utils/poster', () => ({
  resolvePosterUrl: (link: string | null | undefined) => link ?? '',
}));
vi.mock('../ab-search-confirm.vue', () => ({
  default: { name: 'AbSearchConfirm', template: '<div />' },
}));

const IconButtonStub = defineComponent({
  name: 'AbIconButton',
  props: { label: String },
  emits: ['click'],
  template:
    '<button type="button" :aria-label="label" @click="$emit(\'click\')"><slot /></button>',
});

const EmptyPage = defineComponent({
  name: 'EmptyPage',
  template: '<div />',
});

const actions = {
  clearFilters: vi.fn(),
  clearSearch: vi.fn(),
  clearSelectedResult: vi.fn(),
  closeSearch: vi.fn(),
  getAll: vi.fn(),
  getProviders: vi.fn(),
  onSearch: vi.fn(),
  selectResult: vi.fn(),
};
const selectedResult = ref<Record<string, never> | null>(null);

const mountedWrappers: VueWrapper[] = [];

function mountPanel(dismissible = false) {
  const wrapper = shallowMount(AbSearchPanel, {
    attachTo: document.body,
    props: { dismissible },
    global: {
      mocks: {
        $t: (key: string) => key,
      },
      stubs: {
        AbIconButton: IconButtonStub,
      },
    },
  });
  mountedWrappers.push(wrapper);
  return wrapper;
}

function mountKeptPanel() {
  const active = ref(true);
  const Host = defineComponent({
    components: { AbSearchPanel, EmptyPage },
    setup() {
      return { active };
    },
    template: `
      <KeepAlive>
        <AbSearchPanel v-if="active" />
        <EmptyPage v-else />
      </KeepAlive>
    `,
  });
  const wrapper = mount(Host, {
    attachTo: document.body,
    global: {
      mocks: {
        $t: (key: string) => key,
      },
      stubs: {
        AbIconButton: IconButtonStub,
      },
    },
  });
  mountedWrappers.push(wrapper);
  return { active, wrapper };
}

describe('ab-search-panel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    selectedResult.value = null;
    vi.mocked(useMessage).mockReturnValue({
      error: vi.fn(),
      success: vi.fn(),
    } as unknown as ReturnType<typeof useMessage>);
    vi.mocked(useMyI18n).mockReturnValue({
      t: (key: string) => key,
    } as ReturnType<typeof useMyI18n>);
    vi.mocked(useBangumiStore).mockReturnValue({
      getAll: actions.getAll,
    } as unknown as ReturnType<typeof useBangumiStore>);
    vi.mocked(useSearchStore).mockReturnValue({
      providers: ref(['mikan']),
      provider: ref('mikan'),
      loading: ref(false),
      searchFailed: ref(false),
      inputValue: ref(''),
      groupedResults: ref([]),
      selectedResult,
      activeFilters: ref({
        group: [],
        resolution: [],
        subtitle: [],
        season: [],
      }),
      clearFilters: actions.clearFilters,
      clearSearch: actions.clearSearch,
      clearSelectedResult: actions.clearSelectedResult,
      closeSearch: actions.closeSearch,
      getProviders: actions.getProviders,
      onSearch: actions.onSearch,
      selectResult: actions.selectResult,
    } as unknown as ReturnType<typeof useSearchStore>);
  });

  afterEach(() => {
    for (const wrapper of mountedWrappers.splice(0)) {
      wrapper.unmount();
    }
  });

  it('should not create a dialog landmark when rendered as page content', () => {
    const wrapper = mountPanel();

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
  });

  it('should hide the dismiss control when dismissible is false', () => {
    const wrapper = mountPanel();

    expect(wrapper.find('[aria-label="common.close"]').exists()).toBe(false);
  });

  it('should show the dismiss control when dismissible is true', () => {
    const wrapper = mountPanel(true);

    expect(wrapper.find('[aria-label="common.close"]').exists()).toBe(true);
  });

  it('should emit dismiss when the dismiss control is pressed', async () => {
    const wrapper = mountPanel(true);

    await wrapper.get('[aria-label="common.close"]').trigger('click');

    expect(wrapper.emitted('dismiss')).toHaveLength(1);
  });

  it('should focus the search input when mounted', async () => {
    const wrapper = mountPanel();
    await nextTick();

    expect(document.activeElement).toBe(wrapper.get('input').element);
  });

  it('should expose focusInput when a parent controls activation', () => {
    const wrapper = mountPanel();
    const vm = wrapper.vm as ComponentPublicInstance & {
      focusInput?: () => void;
    };

    expect(typeof vm.focusInput).toBe('function');
  });

  it('should describe the provider disclosure without claiming listbox behavior', () => {
    const wrapper = mountPanel();
    const trigger = wrapper.get('.provider-btn');
    const options = wrapper.get('.provider-dropdown');
    const controls = trigger.attributes('aria-controls');

    expect([
      trigger.attributes('aria-haspopup'),
      Boolean(controls) && controls === options.attributes('id'),
    ]).toEqual([undefined, true]);
  });

  it('should ignore Escape when a kept search panel is deactivated', async () => {
    selectedResult.value = {};
    const { active } = mountKeptPanel();
    active.value = false;
    await nextTick();
    actions.clearSelectedResult.mockClear();

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

    expect(actions.clearSelectedResult).not.toHaveBeenCalled();
  });
});
