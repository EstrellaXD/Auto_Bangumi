import type { BangumiRule } from '#/bangumi';

export const useBangumiStore = defineStore('bangumi', () => {
  const data = ref<BangumiRule[]>();

  function getAll() {
    const { execute, onResult } = useApi(apiBangumi.getAll);

    function sort(arr: BangumiRule[]) {
      return arr.sort((a, b) => b.id - a.id);
    }

    onResult((res) => {
      const enabled = sort(res.filter((e) => !e.deleted));
      const disabled = sort(res.filter((e) => e.deleted));

      data.value = [...enabled, ...disabled];
    });

    execute();
  }

  function useUpdateRule() {
    const { execute, onResult } = useApi(apiBangumi.updateRule);

    return {
      execute,
      onResult,
    };
  }

  function useDisableRule() {
    const { execute, onResult } = useApi(apiBangumi.disableRule);

    return {
      execute,
      onResult,
    };
  }

  function useEnableRule() {
    const { execute, onResult } = useApi(apiBangumi.enableRule);

    return {
      execute,
      onResult,
    };
  }

  function useDeleteRule() {
    const { execute, onResult } = useApi(apiBangumi.deleteRule);

    return {
      execute,
      onResult,
    };
  }

  return {
    data,
    getAll,
    useUpdateRule,
    useDisableRule,
    useEnableRule,
    useDeleteRule,
  };
});
