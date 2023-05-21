import type { BangumiItem } from '#/bangumi';

export const useBangumiStore = defineStore('bangumi', () => {
  const data = ref<BangumiItem[]>();

  const getAll = async () => {
    const res = await apiBangumi.getAll();
    data.value = res;
  };

  return { data, getAll };
});
