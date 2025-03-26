import type { Ref } from 'vue';
import { omit } from 'radash';
import type { BangumiAPI, BangumiRule } from '#/bangumi';

type EventSourceStatus = 'OPEN' | 'CONNECTING' | 'CLOSED';

export const apiSearch = {
  get() {
    const eventSource = ref(null) as Ref<EventSource | null>;
    const status = ref<EventSourceStatus>('CLOSED');
    const data = ref<BangumiRule[]>([]);

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
        status.value = 'OPEN';
      };
      es.onmessage = (e) => {
        const _data = JSON.parse(e.data) as BangumiAPI;
        const newData: BangumiRule = {
          ...omit(_data, ['filter', 'rss_link']),
          filter: _data.filter.split(','),
          rss_link: _data.rss_link.split(','),
        };
        data.value = [...data.value, newData];
      };
      es.onerror = (err) => {
        console.error('EventSource error:', err);
        close();
      };
    };

    const open = () => {
      data.value = [];
      _init();
    };

    return {
      keyword,
      provider,
      status,
      data,
      open,
      close,
    };
  },

  async getProvider() {
    const { data } = await axios.get<string[]>('api/v1/search/provider');
    return data;
  },
};
