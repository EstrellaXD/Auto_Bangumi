import type { BangumiItem } from '#/bangumi';

interface Status {
  status: 'Success' | 'Failed to parse link';
}

export const apiDownload = {
  /**
   * 解析 RSS 链接
   * @param rss_link - RSS 链接
   */
  async analysis(rss_link: string) {
    const { data } = await axios.post<BangumiItem>('api/v1/download/analysis', {
      rss_link,
    });
    return data;
  },

  /**
   * 旧番
   * @param bangumiData - Bangumi 数据
   */
  async collection(bangumiData: BangumiItem) {
    const { data } = await axios.post<Status>(
      'api/v1/download/collection',
      bangumiData
    );
    return data.status === 'Success';
  },

  /**
   * 新番
   * @param bangumiData - Bangumi 数据
   */
  async subscribe(bangumiData: BangumiItem) {
    const { data } = await axios.post<Status>(
      'api/v1/download/subscribe',
      bangumiData
    );
    return data.status === 'Success';
  },
};
