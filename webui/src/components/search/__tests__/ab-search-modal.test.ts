import { defineComponent, ref } from 'vue';
import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AbSearchModal from '../ab-search-modal.vue';
import { useSearchStore } from '@/store/search';

vi.mock('@/api/download', () => ({
  apiDownload: { subscribe: vi.fn() },
}));
vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ error: vi.fn(), success: vi.fn() }),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));
vi.mock('@/store/bangumi', () => ({
  useBangumiStore: () => ({ getAll: vi.fn() }),
}));
vi.mock('@/store/search', () => ({ useSearchStore: vi.fn() }));
vi.mock('@/utils/poster', () => ({
  resolvePosterUrl: (link: string | null | undefined) => link ?? '',
}));
vi.mock('../ab-search-confirm.vue', () => ({
  default: { name: 'AbSearchConfirm', template: '<div />' },
}));

const SearchPanelStub = defineComponent({
  name: 'AbSearchPanel',
  props: { dismissible: Boolean },
  emits: ['dismiss', 'subscribed'],
  template: `
    <section data-search-panel-stub :data-dismissible="dismissible">
      <button data-emit-dismiss @click="$emit('dismiss')">dismiss</button>
      <button data-emit-subscribed @click="$emit('subscribed')">subscribed</button>
    </section>
  `,
});

const showModal = ref(false);
const actions = {
  clearSearch: vi.fn(),
  clearSelectedResult: vi.fn(),
  closeSearch: vi.fn(),
  closeModal: vi.fn(() => {
    showModal.value = false;
  }),
  getProviders: vi.fn(),
  onSearch: vi.fn(),
  selectResult: vi.fn(),
};

function mountModal() {
  return mount(AbSearchModal, {
    global: {
      stubs: {
        AbSearchPanel: SearchPanelStub,
        Teleport: true,
        Transition: false,
      },
    },
  });
}

describe('ab-search-modal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    showModal.value = false;
    vi.mocked(useSearchStore).mockReturnValue({
      showModal,
      providers: ref(['mikan']),
      provider: ref('mikan'),
      loading: ref(false),
      searchFailed: ref(false),
      inputValue: ref(''),
      groupedResults: ref([]),
      selectedResult: ref(null),
      clearSearch: actions.clearSearch,
      clearSelectedResult: actions.clearSelectedResult,
      closeSearch: actions.closeSearch,
      closeModal: actions.closeModal,
      getProviders: actions.getProviders,
      onSearch: actions.onSearch,
      selectResult: actions.selectResult,
    } as unknown as ReturnType<typeof useSearchStore>);
  });

  it('should not mount the search panel when the modal is closed', () => {
    const wrapper = mountModal();

    expect(wrapper.find('[data-search-panel-stub]').exists()).toBe(false);
  });

  it('should render a dialog landmark when the modal is open', () => {
    showModal.value = true;
    const wrapper = mountModal();

    expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
  });

  it('should make the panel dismissible when the modal is open', () => {
    showModal.value = true;
    const wrapper = mountModal();

    expect(
      wrapper.get('[data-search-panel-stub]').attributes('data-dismissible')
    ).toBe('true');
  });

  it('should clear search state when the user dismisses the modal', async () => {
    showModal.value = true;
    const wrapper = mountModal();

    await wrapper.get('[data-emit-dismiss]').trigger('click');

    expect(actions.clearSearch).toHaveBeenCalledTimes(1);
  });

  it('should close the modal when a subscription succeeds', async () => {
    showModal.value = true;
    const wrapper = mountModal();

    await wrapper.get('[data-emit-subscribed]').trigger('click');

    expect(showModal.value).toBe(false);
  });

  it('should preserve search state when a subscription closes the modal', async () => {
    showModal.value = true;
    const wrapper = mountModal();

    await wrapper.get('[data-emit-subscribed]').trigger('click');

    expect(actions.clearSearch).not.toHaveBeenCalled();
  });
});
