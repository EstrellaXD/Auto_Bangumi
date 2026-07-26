import { defineComponent, nextTick, ref } from 'vue';
import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AbSearchBar from '../ab-search-bar.vue';
import { useSearchStore } from '@/store/search';

vi.mock('@/store/search', () => ({ useSearchStore: vi.fn() }));
vi.mock('../search/ab-search-modal.vue', () => ({
  default: { name: 'AbSearchModal', template: '<div />' },
}));

const SearchTriggerStub = defineComponent({
  name: 'AbSearch',
  emits: ['click'],
  template:
    '<button data-search-trigger @click="$emit(\'click\')">search</button>',
});

const showModal = ref(false);
const actions = {
  closeModal: vi.fn(() => {
    showModal.value = false;
  }),
  getProviders: vi.fn(),
  openModal: vi.fn(() => {
    showModal.value = true;
  }),
  toggleModal: vi.fn(),
};
const wrappers: ReturnType<typeof mount>[] = [];

function mountSearchBar() {
  const wrapper = mount(AbSearchBar, {
    attachTo: document.body,
    global: {
      stubs: {
        AbSearch: SearchTriggerStub,
      },
    },
  });
  wrappers.push(wrapper);
  return wrapper;
}

describe('ab-search-bar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    showModal.value = false;
    vi.mocked(useSearchStore).mockReturnValue({
      showModal,
      provider: ref('mikan'),
      loading: ref(false),
      closeModal: actions.closeModal,
      getProviders: actions.getProviders,
      openModal: actions.openModal,
      toggleModal: actions.toggleModal,
    } as unknown as ReturnType<typeof useSearchStore>);
  });

  afterEach(() => {
    for (const wrapper of wrappers.splice(0)) wrapper.unmount();
  });

  it('should open the desktop modal when the search trigger is pressed', async () => {
    const wrapper = mountSearchBar();

    await wrapper.get('[data-search-trigger]').trigger('click');

    expect(actions.openModal).toHaveBeenCalledTimes(1);
  });

  it('should let the mounted search panel load providers once', () => {
    mountSearchBar();

    expect(actions.getProviders).not.toHaveBeenCalled();
  });

  it('should restore focus to the trigger when the modal closes', async () => {
    const wrapper = mountSearchBar();
    const trigger = wrapper.get<HTMLButtonElement>('[data-search-trigger]');
    showModal.value = true;
    await nextTick();

    showModal.value = false;
    await nextTick();

    expect(document.activeElement === trigger.element).toBe(true);
  });

  it('should close the modal when the search trigger unmounts', () => {
    showModal.value = true;
    const wrapper = mountSearchBar();

    wrapper.unmount();

    expect(actions.closeModal).toHaveBeenCalledTimes(1);
  });
});
