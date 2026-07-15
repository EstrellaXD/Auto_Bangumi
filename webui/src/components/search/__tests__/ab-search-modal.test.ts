import { defineComponent, ref } from 'vue';
import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
const inputValue = ref('');
const actions = {
  clearFilters: vi.fn(),
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
    attachTo: document.body,
    global: {
      stubs: {
        AbSearchPanel: SearchPanelStub,
      },
    },
  });
}

function mountIntegratedModal() {
  return mount(AbSearchModal, {
    attachTo: document.body,
    global: {
      stubs: {
        AbIconButton: true,
      },
    },
  });
}

afterEach(() => {
  document.body.innerHTML = '';
});

describe('ab-search-modal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    showModal.value = false;
    inputValue.value = '';
    vi.mocked(useSearchStore).mockReturnValue({
      showModal,
      providers: ref(['mikan']),
      provider: ref('mikan'),
      loading: ref(false),
      searchFailed: ref(false),
      inputValue,
      groupedResults: ref([]),
      selectedResult: ref(null),
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
      closeModal: actions.closeModal,
      getProviders: actions.getProviders,
      onSearch: actions.onSearch,
      selectResult: actions.selectResult,
    } as unknown as ReturnType<typeof useSearchStore>);
  });

  it('should not mount the search panel when the modal is closed', () => {
    const wrapper = mountModal();

    expect(document.querySelector('[data-search-panel-stub]')).toBeNull();
    wrapper.unmount();
  });

  it('should render a dialog landmark when the modal is open', async () => {
    showModal.value = true;
    const wrapper = mountModal();
    await new Promise((resolve) => setTimeout(resolve));

    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    wrapper.unmount();
  });

  it('should make the panel dismissible when the modal is open', async () => {
    showModal.value = true;
    const wrapper = mountModal();
    await new Promise((resolve) => setTimeout(resolve));

    expect(
      document
        .querySelector('[data-search-panel-stub]')
        ?.getAttribute('data-dismissible')
    ).toBe('true');
    wrapper.unmount();
  });

  it('should clear search state when the user dismisses the modal', async () => {
    showModal.value = true;
    const wrapper = mountModal();
    await new Promise((resolve) => setTimeout(resolve));

    (
      document.querySelector('[data-emit-dismiss]') as HTMLButtonElement
    ).click();
    await new Promise((resolve) => setTimeout(resolve));

    expect(actions.clearSearch).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it('should close the modal when a subscription succeeds', async () => {
    showModal.value = true;
    const wrapper = mountModal();
    await new Promise((resolve) => setTimeout(resolve));

    (
      document.querySelector('[data-emit-subscribed]') as HTMLButtonElement
    ).click();
    await new Promise((resolve) => setTimeout(resolve));

    expect(showModal.value).toBe(false);
    wrapper.unmount();
  });

  it('should preserve search state when a subscription closes the modal', async () => {
    showModal.value = true;
    const wrapper = mountModal();
    await new Promise((resolve) => setTimeout(resolve));

    (
      document.querySelector('[data-emit-subscribed]') as HTMLButtonElement
    ).click();
    await new Promise((resolve) => setTimeout(resolve));

    expect(actions.clearSearch).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it('should dismiss the modal when Escape is pressed', async () => {
    showModal.value = true;
    const wrapper = mountModal();
    await new Promise((resolve) => setTimeout(resolve));

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
    );
    await new Promise((resolve) => setTimeout(resolve));

    expect(actions.clearSearch).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it('should close only the provider disclosure when Escape is pressed on its focused trigger', async () => {
    showModal.value = true;
    inputValue.value = 'Frieren';
    const wrapper = mountIntegratedModal();
    await new Promise((resolve) => setTimeout(resolve));
    const providerTrigger = document.querySelector<HTMLButtonElement>(
      '.provider-btn'
    ) as HTMLButtonElement;
    providerTrigger.click();
    await new Promise((resolve) => setTimeout(resolve));
    providerTrigger.focus();

    providerTrigger.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'Escape',
        bubbles: true,
        cancelable: true,
      })
    );
    await new Promise((resolve) => setTimeout(resolve));

    expect([
      document.querySelector('.provider-dropdown') !== null,
      showModal.value,
      actions.clearSearch.mock.calls.length,
      inputValue.value,
      document.activeElement === providerTrigger,
    ]).toEqual([false, true, 0, 'Frieren', true]);
    wrapper.unmount();
  });

  it('should move focus inside the modal when it opens', async () => {
    showModal.value = true;
    const wrapper = mountModal();
    await new Promise((resolve) => setTimeout(resolve));

    expect(
      document
        .querySelector('[role="dialog"]')
        ?.contains(document.activeElement)
    ).toBe(true);
    wrapper.unmount();
  });
});
