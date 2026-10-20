import { createSharedComposable } from '@vueuse/core';
import type { QbTorrentInfo } from '#/downloader';
import type { UpdateProgress } from '#/update';

export interface StatusPayload {
  status: boolean;
  version: string;
  first_run: boolean;
}

export interface NotificationStreamPayload {
  unread_count: number;
  latest_id: number;
  revision: number;
}

/** SSE `bus` 帧：事件总线上宿主与插件发布的事件 */
export interface BusEvent {
  kind: string;
  payload: unknown;
}

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 15000;
/** 标签页持续隐藏超过该时长后关闭流，可见时重连（服务端重发快照） */
const HIDDEN_CLOSE_DELAY_MS = 30000;
/** 累积日志文本的上限，与后端 /log 的尾部读取预算一致 */
const LOG_MAX_CHARS = 512 * 1024;

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
  const updateData = ref<UpdateProgress | null>(null);
  const notificationData = ref<NotificationStreamPayload | null>(null);

  const busListeners = new Map<string, Set<(payload: unknown) => void>>();

  /** 订阅总线事件 `kind`；连接中断重连期间发布的事件不会补发。返回取消函数 */
  function onBus(kind: string, callback: (payload: unknown) => void) {
    const listeners = busListeners.get(kind) ?? new Set();
    listeners.add(callback);
    busListeners.set(kind, listeners);
    return () => {
      listeners.delete(callback);
    };
  }

  let source: EventSource | null = null;
  let retryCount = 0;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let hiddenTimer: ReturnType<typeof setTimeout> | undefined;
  /** 因标签页长时间隐藏而主动关闭；此状态下不重连，直到页面可见 */
  let suspended = false;

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
      if (isLoggedIn.value && !suspended) connect();
    }, delay);
  }

  function connect() {
    if (!isLoggedIn.value || typeof EventSource === 'undefined') {
      return;
    }
    teardown();

    const es = new EventSource('api/v1/events/stream', {
      withCredentials: true,
    });
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

    // EventSource 不派发 data 为空的事件，空日志由服务端改推 log_clear
    es.addEventListener('log_clear', () => {
      logData.value = '';
    });

    es.addEventListener('log_append', (e) => {
      const text = (logData.value ?? '') + (e as MessageEvent).data;
      if (text.length <= LOG_MAX_CHARS) {
        logData.value = text;
        return;
      }
      // 超出上限时丢弃最旧部分，并对齐到下一行起点
      const tail = text.slice(text.length - LOG_MAX_CHARS);
      logData.value = tail.slice(tail.indexOf('\n') + 1);
    });

    es.addEventListener('update', (e) => {
      try {
        updateData.value = JSON.parse((e as MessageEvent).data);
      } catch {
        // Ignore malformed frames; the next tick will retry.
      }
    });

    es.addEventListener('notification', (e) => {
      try {
        notificationData.value = JSON.parse((e as MessageEvent).data);
      } catch {
        // Ignore malformed frames; the next tick will retry.
      }
    });

    es.addEventListener('bus', (e) => {
      try {
        const { kind, payload } = JSON.parse(
          (e as MessageEvent).data
        ) as BusEvent;
        // 回调出错不能影响其它订阅者与后续帧
        busListeners.get(kind)?.forEach((callback) => {
          try {
            callback(payload);
          } catch (error) {
            console.error(`bus listener for ${kind} failed`, error);
          }
        });
      } catch {
        // Ignore malformed frames.
      }
    });

    es.onerror = () => {
      teardown();
      scheduleReconnect();
    };
  }

  function stop() {
    clearTimeout(retryTimer);
    clearTimeout(hiddenTimer);
    suspended = false;
    retryCount = 0;
    teardown();
  }

  function onVisibilityChange() {
    clearTimeout(hiddenTimer);
    if (document.hidden) {
      hiddenTimer = setTimeout(() => {
        suspended = true;
        clearTimeout(retryTimer);
        teardown();
      }, HIDDEN_CLOSE_DELAY_MS);
    } else if (suspended) {
      suspended = false;
      retryCount = 0;
      if (isLoggedIn.value) connect();
    }
  }
  document.addEventListener('visibilitychange', onVisibilityChange);

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
    updateData,
    notificationData,
    onBus,
  };
});
