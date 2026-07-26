/* eslint-disable vue/one-component-per-file */
import { defineComponent, nextTick, ref } from 'vue';
import type { Component } from 'vue';
import { mount } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSearchStore } from '@/store/search';

vi.mock('@/store/search', () => ({ useSearchStore: vi.fn() }));

const focusInput = vi.fn();

vi.mock('@/components/search/ab-search-panel.vue', () => ({
  default: {
    name: 'AbSearchPanel',
    methods: { focusInput },
    template: '<section data-search-panel-stub />',
  },
}));

const EmptyPage = defineComponent({
  name: 'EmptyPage',
  template: '<div />',
});

const inputValue = ref('Frieren');
const groupedResults = ref([{ key: 'frieren' }]);
const actions = {
  clearSearch: vi.fn(() => {
    inputValue.value = '';
    groupedResults.value = [];
  }),
  clearSelectedResult: vi.fn(),
  closeSearch: vi.fn(),
};

let SearchPage: Component;

function mountSearchPage() {
  return mount(SearchPage);
}

function mountKeptSearchPage() {
  const active = ref(true);
  const Host = defineComponent({
    components: { EmptyPage, SearchPage },
    setup() {
      return { active };
    },
    template: `
      <KeepAlive>
        <SearchPage v-if="active" />
        <EmptyPage v-else />
      </KeepAlive>
    `,
  });
  const wrapper = mount(Host);
  return { active, wrapper };
}

describe('search page', () => {
  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    SearchPage = (await import('./search.vue')).default;
  });

  beforeEach(() => {
    vi.clearAllMocks();
    inputValue.value = 'Frieren';
    groupedResults.value = [{ key: 'frieren' }];
    vi.mocked(useSearchStore).mockReturnValue({
      inputValue,
      groupedResults,
      clearSearch: actions.clearSearch,
      clearSelectedResult: actions.clearSelectedResult,
      closeSearch: actions.closeSearch,
    } as unknown as ReturnType<typeof useSearchStore>);
  });

  it('should mount the reusable search panel when the route renders', () => {
    const wrapper = mountSearchPage();

    expect(wrapper.find('[data-search-panel-stub]').exists()).toBe(true);
  });

  it('should close the active search stream when the kept page deactivates', async () => {
    const { active } = mountKeptSearchPage();
    actions.closeSearch.mockClear();

    active.value = false;
    await nextTick();

    expect(actions.closeSearch).toHaveBeenCalledTimes(1);
  });

  it('should preserve query and results when the kept page deactivates', async () => {
    const { active } = mountKeptSearchPage();

    active.value = false;
    await nextTick();

    expect({
      query: inputValue.value,
      results: groupedResults.value.length,
    }).toEqual({ query: 'Frieren', results: 1 });
  });

  it('should clear the transient confirmation when the kept page deactivates', async () => {
    const { active } = mountKeptSearchPage();
    actions.clearSelectedResult.mockClear();

    active.value = false;
    await nextTick();

    expect(actions.clearSelectedResult).toHaveBeenCalledTimes(1);
  });

  it('should focus the panel when the kept page reactivates', async () => {
    const { active } = mountKeptSearchPage();
    focusInput.mockClear();
    active.value = false;
    await nextTick();

    active.value = true;
    await nextTick();

    expect(focusInput).toHaveBeenCalledTimes(1);
  });
});
