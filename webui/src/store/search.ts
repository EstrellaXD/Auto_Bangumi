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

  async function getProviders() {
    providers.value = await apiSearch.getProvider();
    provider.value = providers.value[0];
  }

  function clearSearch() {
    keyword.value = '';
  }

  return {
    keyword,
    loading,
    provider,
    providers,
    searchData,

    clearSearch,
    getProviders,
    openSearch,
    closeSearch,
  };
});
