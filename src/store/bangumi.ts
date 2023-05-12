import { getABData } from '../api/bangumi';
import type { BangumiItem } from '#/bangumi';

export const bangumiStore = defineStore('bangumi', () => {
  const data = ref<BangumiItem[]>();

  const get = async () => {
    const res = await getABData();
    data.value = res.data;
  };

  return { data, get };
});
