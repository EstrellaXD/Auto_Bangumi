import type { BangumiRule } from '#/bangumi';
import { ruleTemplate } from '#/bangumi';

export const useBangumiStore = defineStore('bangumi', () => {
  const bangumi = ref<BangumiRule[]>([]);
  const showArchived = ref(false);
  const isLoading = ref(false);
  const hasLoaded = ref(false);
  const editRule = reactive<{
    show: boolean;
    item: BangumiRule;
  }>({
    show: false,
    item: { ...ruleTemplate },
  });

  // Computed: active bangumi (not deleted, not archived)
  const activeBangumi = computed(() =>
    bangumi.value.filter((b) => !b.deleted && !b.archived)
  );

  // Computed: archived bangumi (not deleted, archived)
  const archivedBangumi = computed(() =>
    bangumi.value.filter((b) => !b.deleted && b.archived)
  );

  async function getAll() {
    isLoading.value = true;
    try {
      const res = await apiBangumi.getAll();
      const sort = (arr: BangumiRule[]) => arr.sort((a, b) => b.id - a.id);

      const enabled = sort(res.filter((e) => !e.deleted));
      const disabled = sort(res.filter((e) => e.deleted));

      bangumi.value = [...enabled, ...disabled];
      hasLoaded.value = true;
    } finally {
      isLoading.value = false;
    }
  }

  function refreshData() {
    editRule.show = false;
    getAll();
  }

  const opts = {
    showMessage: true,
    onSuccess() {
      refreshData();
    },
  };

  const { execute: updateRule } = useApi(apiBangumi.updateRule, opts);
  const { execute: enableRule } = useApi(apiBangumi.enableRule, opts);
  const { execute: disableRule } = useApi(apiBangumi.disableRule, opts);
  const { execute: deleteRule } = useApi(apiBangumi.deleteRule, opts);
  const { execute: refreshPoster } = useApi(apiBangumi.refreshPoster, opts);
  const { execute: archiveRule } = useApi(apiBangumi.archiveRule, opts);
  const { execute: unarchiveRule } = useApi(apiBangumi.unarchiveRule, opts);
  const { execute: refreshMetadata } = useApi(apiBangumi.refreshMetadata, opts);

  function openEditPopup(data: BangumiRule) {
    editRule.show = true;
    editRule.item = data;
  }

  function ruleManage(
    type: 'disable' | 'delete',
    id: number,
    deleteFile: boolean
  ) {
    switch (type) {
      case 'disable':
        disableRule(id, deleteFile);
        break;

      case 'delete':
        deleteRule(id, deleteFile);
        break;
    }
  }

  return {
    bangumi,
    showArchived,
    isLoading,
    hasLoaded,
    activeBangumi,
    archivedBangumi,
    editRule,

    getAll,
    updateRule,
    enableRule,
    disableRule,
    deleteRule,
    refreshPoster,
    archiveRule,
    unarchiveRule,
    refreshMetadata,
    openEditPopup,
    ruleManage,
  };
});
