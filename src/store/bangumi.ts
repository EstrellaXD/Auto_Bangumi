import { defineStore } from 'pinia';
import { getABData } from '../api/bangumi';

export const bangumiStore = defineStore('bangumi', () => {
  const data = ref({ rss_link: '', data_version: 4, bangumi_info: [] });

  const get = async () => {
    const res = await getABData();
    data.value = res.data;
  };

  return { data, get };
});
