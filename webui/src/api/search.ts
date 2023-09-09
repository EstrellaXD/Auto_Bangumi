import {
  Observable,
} from 'rxjs';

import type { BangumiRule, BangumiAPI } from '#/bangumi';

export const apiSearch = {
  /**
   * 番剧搜索接口是 Server Send 流式数据，每条是一个 Bangumi JSON 字符串，
   * 使用接口方式是监听连接消息后，转为 Observable 配合外层调用时 switchMap 订阅使用
   */
  get(keyword: string, site = 'mikan'): Observable<BangumiRule> { 
    const bangumiInfo$ = new Observable<BangumiRule>(observer => {
      const eventSource = new EventSource(
        `api/v1/search/bangumi?site=${site}&keywords=${encodeURIComponent(keyword)}`,
        { withCredentials: true },
      );

      eventSource.onmessage = ev => {
        try {
          const apiData: BangumiAPI = JSON.parse(ev.data);
            const data: BangumiRule = {
                ...apiData,
                filter: apiData.filter.split(','),
                rss_link: apiData.rss_link.split(','),
            }
          observer.next(data);
        } catch (error) {
          console.error('[/search/bangumi] Parse Error |', { keyword }, 'response:', ev.data)
        }
      };

      eventSource.onerror = ev => {
        console.error('[/search/bangumi] Server Error |', { keyword }, 'error:', ev)
        // 目前后端搜索完成关闭连接时会触发 error 事件，前端手动调用 close 不再自动重连
        eventSource.close();
      };

      return () => {
        eventSource.close();
      };
    });

    return bangumiInfo$;
  },

  async getProvider() {
    const { data } = await axios.get<string[]>('api/v1/search/provider');
    return data;
  }
};

