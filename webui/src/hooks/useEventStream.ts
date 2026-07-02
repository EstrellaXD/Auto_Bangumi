import { createSharedComposable } from '@vueuse/core';
import type { QbTorrentInfo } from '#/downloader';

export interface StatusPayload {
  status: boolean;
  version: string;
  first_run: boolean;
}

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 15000;

/**
 * 单一 SSE 连接（api/v1/events/stream），推送 status/downloader/log 更新，
 * 取代原本 useAppInfo/downloader.vue/log store 各自的轮询循环。
 *
 * `connected` 供三个消费者判断：为 true 时它们跳过自己的轮询请求，改用
 * `statusData`/`downloaderData`/`logData`；连接断开或环境不支持
 * EventSource 时，`connected` 保持 false，消费者据此回退到原有轮询。
 */
export const useEventStream = createSharedComposable(() => {
  const { isLoggedIn } = useAuth();

  const connected = ref(false);
  const statusData = ref<StatusPayload | null>(null);
  const downloaderData = ref<QbTorrentInfo[] | null>(null);
  const logData = ref<string | null>(null);

  let source: EventSource | null = null;
  let retryCount = 0;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;

  function teardown() {
    source?.close();
    source = null;
    connected.value = false;
  }

  function scheduleReconnect() {
    clearTimeout(retryTimer);
    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * 2 ** retryCount,
      RECONNECT_MAX_DELAY_MS
    );
    retryCount += 1;
    retryTimer = setTimeout(() => {
      if (isLoggedIn.value) connect();
    }, delay);
  }

  function connect() {
    if (!isLoggedIn.value || typeof EventSource === 'undefined') {
      return;
    }
    teardown();

    const es = new EventSource('api/v1/events/stream', { withCredentials: true });
    source = es;

    es.onopen = () => {
      connected.value = true;
      retryCount = 0;
    };

    es.addEventListener('status', (e) => {
      try {
        statusData.value = JSON.parse((e as MessageEvent).data);
      } catch {
        // Ignore malformed frames; the next tick will retry.
      }
    });

    es.addEventListener('downloader', (e) => {
      try {
        downloaderData.value = JSON.parse((e as MessageEvent).data);
      } catch {
        // Ignore malformed frames; the next tick will retry.
      }
    });

    es.addEventListener('log', (e) => {
      logData.value = (e as MessageEvent).data;
    });

    es.onerror = () => {
      teardown();
      scheduleReconnect();
    };
  }

  function stop() {
    clearTimeout(retryTimer);
    retryCount = 0;
    teardown();
  }

  // 生命周期跟随登录状态，而非某个调用方组件的挂载/卸载——这是一个跨组件
  // 共享的单例连接（createSharedComposable），不能绑定到任意一个消费者的
  // onBeforeUnmount 上。
  watch(
    isLoggedIn,
    (loggedIn) => {
      if (loggedIn) {
        connect();
      } else {
        stop();
      }
    },
    { immediate: true }
  );

  return {
    connected,
    statusData,
    downloaderData,
    logData,
  };
});
