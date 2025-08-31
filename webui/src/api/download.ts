import type { BangumiAPI, BangumiRule } from '#/bangumi';
import type { RSS } from '#/rss';
import type { ApiSuccess } from '#/api';

export const apiDownload = {
  /**
   * 解析 RSS 链接
   * @param rss_item - RSS 链接
   */
  async analysis(rss_item: RSS) {
    const { data } = await axios.post<BangumiAPI>(
      'api/v1/rss/analysis',
      rss_item
    );

    const result: BangumiRule = {
      ...data,
      include_filter: data.include_filter.split(','),
      exclude_filter: data.exclude_filter.split(','),
    };
    return result;
  },

  /**
   * 旧番
   * @param bangumiData - Bangumi 数据
   */
  async collection(bangumiData: BangumiRule) {
    const postData: BangumiAPI = {
      ...bangumiData,
      include_filter: bangumiData.include_filter.join(','),
      exclude_filter: bangumiData.exclude_filter.join(','),
    };
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/rss/collect',
      postData
    );
    return data;
  },

  /**
   * 新番
   * @param bangumiData - Bangumi 数据
   */
  async subscribe(bangumiData: BangumiRule, rss: RSS) {
    const bangumi: BangumiAPI = {
      ...bangumiData,
      include_filter: bangumiData.include_filter.join(','),
      exclude_filter: bangumiData.exclude_filter.join(','),
    };
    const postData = {
      data: bangumi,
      rss,
    };
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/rss/subscribe',
      postData
    );
    return data;
  },
};
