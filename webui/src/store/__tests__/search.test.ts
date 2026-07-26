import { createPinia, setActivePinia } from 'pinia';
import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { SearchFilters } from '../search';
import { useSearchStore } from '../search';
import { apiSearch } from '@/api/search';
import { mockBangumiRule } from '@/test/mocks/api';

vi.mock('@/api/search', () => ({
  apiSearch: {
    get: vi.fn(),
    getProvider: vi.fn(),
  },
}));

describe('search store', () => {
  const keyword = ref('');
  const provider = ref('');
  const status = ref<'OPEN' | 'CONNECTING' | 'CLOSED'>('CLOSED');
  const searchData = ref([mockBangumiRule]);
  const searchFailed = ref(false);
  const openSearch = vi.fn();
  const closeSearch = vi.fn(() => {
    status.value = 'CLOSED';
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    keyword.value = '';
    provider.value = '';
    status.value = 'CLOSED';
    searchData.value = [mockBangumiRule];
    searchFailed.value = false;
    vi.mocked(apiSearch.get).mockReturnValue({
      keyword,
      provider,
      status,
      data: searchData,
      error: searchFailed,
      open: openSearch,
      close: closeSearch,
    });
  });

  it('should preserve the keyword when the search stream closes', () => {
    const store = useSearchStore();
    store.inputValue = 'frieren';

    store.closeSearch();

    expect(store.inputValue).toBe('frieren');
  });

  it('should preserve grouped raw results when the search stream closes', () => {
    const store = useSearchStore();

    store.closeSearch();

    expect(store.groupedResults[0]?.variants).toEqual([mockBangumiRule]);
  });

  it('should preserve active filters when the search stream closes', () => {
    const store = useSearchStore() as ReturnType<typeof useSearchStore> & {
      activeFilters: SearchFilters;
    };
    const expected: SearchFilters = {
      group: ['TestGroup'],
      resolution: ['FHD'],
      subtitle: ['繁'],
      season: ['S1'],
    };
    if (store.activeFilters) {
      store.activeFilters = expected;
    }

    store.closeSearch();

    expect(store.activeFilters).toEqual(expected);
  });

  it('should clear the keyword when the search is cleared', () => {
    const store = useSearchStore();
    store.inputValue = 'frieren';

    store.clearSearch();

    expect(store.inputValue).toBe('');
  });

  it('should clear results when the search is cleared', () => {
    const store = useSearchStore();

    store.clearSearch();

    expect(store.groupedResults).toEqual([]);
  });

  it('should keep the current provider when it remains available after refresh', async () => {
    vi.mocked(apiSearch.getProvider).mockResolvedValue(['mikan', 'dmhy']);
    const store = useSearchStore();
    store.provider = 'dmhy';

    await store.getProviders();

    expect(store.provider).toBe('dmhy');
  });

  it('should use the first available provider when the current provider is missing', async () => {
    vi.mocked(apiSearch.getProvider).mockResolvedValue(['dmhy', 'nyaa']);
    const store = useSearchStore();
    store.provider = 'anibt';

    await store.getProviders();

    expect(store.provider).toBe('dmhy');
  });

  it('should use an empty provider when the provider response is empty', async () => {
    vi.mocked(apiSearch.getProvider).mockResolvedValue([]);
    const store = useSearchStore();

    await store.getProviders();

    expect(store.provider).toBe('');
  });
});
