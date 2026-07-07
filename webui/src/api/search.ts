import { omit } from 'radash';
import type { BangumiAPI, BangumiRule } from '#/bangumi';

type EventSourceStatus = 'OPEN' | 'CONNECTING' | 'CLOSED';

export const apiSearch = {
  get() {
    // shallowRef：ref() 会把 EventSource 包成 reactive 代理，
    // 导致下面 `eventSource.value !== es` 的同流判定永远为真
    const eventSource = shallowRef<EventSource | null>(null);
    const status = ref<EventSourceStatus>('CLOSED');
    const data = ref<BangumiRule[]>([]);
    const error = ref(false);

    const keyword = ref('');
    const provider = ref('');

    const close = () => {
      if (eventSource.value) {
        eventSource.value.close();
        eventSource.value = null;
        status.value = 'CLOSED';
      }
    };

    const _init = () => {
      status.value = 'CONNECTING';

      const url = `api/v1/search/bangumi?site=${
        provider.value
      }&keywords=${encodeURIComponent(keyword.value)}`;

      const es = new EventSource(url, { withCredentials: true });
      eventSource.value = es;
      es.onopen = () => {
        if (eventSource.value !== es) return;
        status.value = 'OPEN';
      };
      es.onmessage = (e) => {
        // 已被新一次搜索替换的旧流：关掉自己，不再往结果里追加
        if (eventSource.value !== es) {
          es.close();
          return;
        }
        const _data = JSON.parse(e.data) as BangumiAPI;
        const newData: BangumiRule = {
          ...omit(_data, ['filter', 'rss_link']),
          filter: _data.filter.split(','),
          rss_link: _data.rss_link.split(','),
        };
        // 兜底去重：服务端每条流内已按订阅链接去重，这里防异常场景的重复项
        const id = newData.rss_link?.[0] || newData.title_raw;
        if (data.value.some((d) => (d.rss_link?.[0] || d.title_raw) === id)) {
          return;
        }
        data.value = [...data.value, newData];
      };
      es.onerror = (err) => {
        // 旧流的 onerror 绝不能碰共享状态（会把新流关掉）；但必须 close
        // 自己——不关的话浏览器会对已结束的流无限自动重连（空转）
        if (eventSource.value !== es) {
          es.close();
          return;
        }
        console.error('EventSource error:', err);
        // onerror also fires when the server closes the stream after a
        // successful search — only count it as a failure when the connection
        // never opened (auth/server/network problem).
        if (status.value === 'CONNECTING') {
          error.value = true;
        }
        close();
      };
    };

    const open = () => {
      // 先关上一条流再开新流：不关的话旧流泄漏——结果被重复追加
      // （重复的条目/tag），且服务端关闭后旧流会无限自动重连（空转）
      close();
      data.value = [];
      error.value = false;
      _init();
    };

    return {
      keyword,
      provider,
      status,
      data,
      error,
      open,
      close,
    };
  },

  async getProvider() {
    const { data } = await axios.get<string[]>('api/v1/search/provider');
    return data;
  },
};
