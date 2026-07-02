import type { BangumiRule } from '#/bangumi';

// Filter types
export interface SearchFilters {
  group: string[];
  resolution: string[];
  subtitleType: string[];
  season: string[];
}

export interface FilterOptions {
  group: string[];
  resolution: string[];
  subtitleType: string[];
  season: string[];
}

// Grouped bangumi result
export interface GroupedBangumi {
  key: string;
  official_title: string;
  poster_link: string;
  year?: string | null;
  variants: BangumiRule[];
}

export const useSearchStore = defineStore('search', () => {
  const providers = ref<string[]>(['mikan', 'dmhy', 'nyaa']);

  const {
    keyword,
    provider,
    open: openSearch,
    close: closeSearch,
    data: searchData,
    status,
  } = apiSearch.get();

  provider.value = providers.value[0];

  // Modal state
  const showModal = ref(false);
  const selectedResult = ref<BangumiRule | null>(null);

  const loading = computed(() => status.value !== 'CLOSED');

  // Group results by official_title
  const groupedResults = computed<GroupedBangumi[]>(() => {
    const map = new Map<string, BangumiRule[]>();

    for (const item of searchData.value) {
      const key = item.official_title || item.title_raw || '';
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)!.push(item);
    }

    const groups: GroupedBangumi[] = [];
    for (const [key, variants] of map) {
      // Use the first variant's poster and info
      const first = variants[0];
      groups.push({
        key,
        official_title: first.official_title || first.title_raw || '',
        poster_link: first.poster_link || '',
        year: first.year,
        variants,
      });
    }

    return groups;
  });

  async function getProviders() {
    providers.value = await apiSearch.getProvider();
    provider.value = providers.value[0];
  }

  function openModal() {
    showModal.value = true;
  }

  function closeModal() {
    showModal.value = false;
    selectedResult.value = null;
    closeSearch();
  }

  function toggleModal() {
    if (showModal.value) {
      closeModal();
    } else {
      openModal();
    }
  }

  function clearSearch() {
    keyword.value = '';
    searchData.value = [];
    closeSearch();
  }

  function selectResult(bangumi: BangumiRule) {
    selectedResult.value = bangumi;
  }

  function clearSelectedResult() {
    selectedResult.value = null;
  }

  function onSearch() {
    if (!keyword.value.trim()) {
      return;
    }
    openSearch();
  }

  return {
    // State
    inputValue: keyword,
    loading,
    provider,
    providers,
    groupedResults,
    showModal,
    selectedResult,

    // Actions
    clearSearch,
    getProviders,
    onSearch,
    closeSearch,
    openModal,
    closeModal,
    toggleModal,
    selectResult,
    clearSelectedResult,
  };
});
