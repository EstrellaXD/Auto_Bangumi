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

  const loading = computed(() => status.value !== 'CLOSED');

  const bangumiList = computed(() =>
    searchData.value.map((item, index) => ({ order: index, value: item }))
  );

  async function getProviders() {
    providers.value = await apiSearch.getProvider();
    provider.value = providers.value[0];
  }

  function clearSearch() {
    keyword.value = '';
    searchData.value = [];
    closeSearch();
  }

  return {
    inputValue: keyword,
    loading,
    provider,
    providers,
    bangumiList,

    clearSearch,
    getProviders,
    onSearch: openSearch,
    closeSearch,
  };
});
