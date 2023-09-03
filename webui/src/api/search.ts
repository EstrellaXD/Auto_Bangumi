import {
  Observable,
} from 'rxjs';

import type { BangumiRule } from '#/bangumi';

export const apiSearch = {
  /**
   * 番剧搜索接口是 Server Send 流式数据，每条是一个 Bangumi JSON 字符串，
   * 使用接口方式需要订阅使用
   * 
   * Usage Example:
   * 
   * ```ts
   *   import {
   *     Subject,
   *     tap,
   *     map,
   *     switchMap,
   *     debounceTime,
   *   } from 'rxjs';
   *
   *   
   *   const input$ = new Subject<string>();
   *   const onInput = (e: Event) => input$.next(e.target);
   * 
   *   // vue: <input @input="onInput">
   * 
   *   const bangumiInfo$ = apiSearch.get('魔女之旅');
   *   
   *   // vue: start loading animation
   * 
   *   input$.pipe(
   *     debounceTime(1000),
   *     tap((input: string) => {
   *       console.log('input', input)
   *       // clear Search Result List
   *     }),
   *
   *     // switchMap 把输入 keyword 查询为 bangumiInfo$ 流，多次输入停用前一次查询
   *     switchMap((input: string) => apiSearch(input, site)),
   *
   *     tap((bangumi: BangumiRule) => console.log(bangumi)),
   *     tap((bangumi: BangumiRule) => {
   *       console.log('bangumi', bangumi)
   *       // set bangumi info to Search Result List
   *     }),
   *   ).subscribe({
   *     complete() {
   *       // end of stream, stop loading animation 
   *     },
   *   })
   * ```
   */
  get(keyword: string, site = 'mikan'): Observable<BangumiRule> { 
    const bangumiInfo$ = new Observable<BangumiRule>(observer => {
      const eventSource = new EventSource(
        `api/v1/search?site=${site}&keyword=${encodeURIComponent(keyword)}`,
        { withCredentials: true },
      );

      eventSource.onmessage = ev => {
        try {
          const data: BangumiRule = JSON.parse(ev.data);
          observer.next(data);
        } catch (error) {
          observer.error(error);
        }
      };

      eventSource.onerror = ev => observer.error(ev);

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

