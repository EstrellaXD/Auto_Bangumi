import type { RSS } from '#/rss';

export const useRSSStore = defineStore('rss', () => {
  const rss = ref<RSS[]>([]);
  const selectedRSS = ref<number[]>([]);
  const isLoading = ref(false);
  const hasLoaded = ref(false);
  const loadFailed = ref(false);

  async function getAll() {
    isLoading.value = true;
    try {
      const res = await apiRSS.get();

      function sort(arr: RSS[]) {
        return arr.sort((a, b) => b.id - a.id);
      }

      const enabled = sort(res.filter((e) => e.enabled));
      const disabled = sort(res.filter((e) => !e.enabled));

      rss.value = [...enabled, ...disabled];
      hasLoaded.value = true;
      loadFailed.value = false;
    } catch {
      loadFailed.value = true;
    } finally {
      isLoading.value = false;
    }
  }

  const opts = {
    showMessage: true,
    onSuccess() {
      getAll();
      selectedRSS.value = [];
    },
  };

  const { execute: updateRSS } = useApi(apiRSS.update, opts);
  const { execute: disableRSS } = useApi(apiRSS.disableMany, opts);
  const { execute: deleteRSS } = useApi(apiRSS.deleteMany, opts);
  const { execute: enableRSS } = useApi(apiRSS.enableMany, opts);

  const disableSelected = () => disableRSS(selectedRSS.value);
  const deleteSelected = () => deleteRSS(selectedRSS.value);
  const enableSelected = () => enableRSS(selectedRSS.value);

  // Refresh doesn't touch selectedRSS, so it gets its own onSuccess instead
  // of reusing `opts`.
  const refreshOpts = {
    showMessage: true,
    onSuccess() {
      getAll();
    },
  };

  const { execute: refreshRSS } = useApi(apiRSS.refresh, refreshOpts);
  const { execute: refreshAllRSS, isLoading: isRefreshingAll } = useApi(
    apiRSS.refreshAll,
    refreshOpts
  );

  return {
    rss,
    selectedRSS,
    isLoading,
    hasLoaded,
    loadFailed,

    getAll,
    updateRSS,
    disableRSS,
    deleteRSS,
    enableRSS,
    disableSelected,
    deleteSelected,
    enableSelected,
    refreshRSS,
    refreshAllRSS,
    isRefreshingAll,
  };
});
