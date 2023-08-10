import type { BangumiRule } from '#/bangumi';

interface Status {
  status: 'Success';
}

export const apiDownload = {
  /**
   * 解析 RSS 链接
   * @param rss_link - RSS 链接
   */
  async analysis(rss_link: string) {
    const { data } = await axios.post<BangumiRule & { status?: string }>(
      'api/v1/download/analysis',
      {
        rss_link,
      }
    );

    // 解析失败抛出错误
    if (data.status) {
      throw data;
    }

    return data;
  },

  /**
   * 旧番
   * @param bangumiData - Bangumi 数据
   */
  async collection(bangumiData: BangumiRule) {
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
  async subscribe(bangumiData: BangumiRule) {
    const { data } = await axios.post<Status>(
      'api/v1/download/subscribe',
      bangumiData
    );
    return data.status === 'Success';
  },
};
