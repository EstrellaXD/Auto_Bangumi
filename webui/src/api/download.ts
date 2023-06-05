import type { BangumiRule } from '#/bangumi';

interface Status {
  status: 'Success';
}

interface AnalysisError {
  status: 'Failed to parse link';
}

export const apiDownload = {
  /**
   * 解析 RSS 链接
   * @param rss_link - RSS 链接
   */
  async analysis(rss_link: string) {
    const fetchResult = createEventHook<BangumiRule>();
    const fetchError = createEventHook<AnalysisError>();

    axios
      .post<any>('api/v1/download/analysis', {
        rss_link,
      })
      .then(({ data }) => {
        if (data.status) {
          fetchError.trigger(data as AnalysisError);
        } else {
          fetchResult.trigger(data as BangumiRule);
        }
      });

    return {
      onResult: fetchResult.on,
      onError: fetchError.on,
    };
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
