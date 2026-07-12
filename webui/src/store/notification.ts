import { useIntervalFn } from '@vueuse/core';
import type { InboxMessage } from '@/api/notification';

/** 有 i18n 文案的消息类型；未知 kind 回退到后端存储的 title/body。 */
const KNOWN_KINDS = [
  'rss_failure',
  'download_failure',
  'offset_review',
  'downloader_unavailable',
  'update_available',
  'update_applied',
  'update_failed',
  'llm_auth_failure',
  'llm_plugin_install_failed',
  'rename_conflict',
] as const;

export const useNotificationStore = defineStore('notification', () => {
  const message = useMessage();
  const { t } = useMyI18n();
  const { isLoggedIn } = useAuth();
  const { connected: sseConnected, notificationData } = useEventStream();

  const messages = ref<InboxMessage[]>([]);
  const total = ref(0);
  const unreadCount = ref(0);
  const isLoading = ref(false);
  const panelOpen = ref(false);
  // null = 尚未收到第一帧；第一帧只同步未读数，不为历史积压弹 toast
  let lastLatestId: number | null = null;

  function titleOf(msg: InboxMessage): string {
    if (!(KNOWN_KINDS as readonly string[]).includes(msg.kind)) {
      return msg.title;
    }
    return t(`notifications.kind.${msg.kind}.title`);
  }

  function bodyOf(msg: InboxMessage): string {
    if (!(KNOWN_KINDS as readonly string[]).includes(msg.kind)) {
      return msg.body;
    }
    const payload = msg.payload ?? {};
    if (msg.kind === 'downloader_unavailable') {
      const reason = String(payload.reason || 'unreachable');
      return `${payload.host ?? ''}: ${t(`notifications.reason.${reason}`)}`;
    }
    return t(`notifications.kind.${msg.kind}.body`, payload);
  }

  async function fetchMessages() {
    if (!isLoggedIn.value) return;
    isLoading.value = true;
    try {
      const res = await apiNotification.getMessages({ limit: 50 });
      messages.value = res.messages;
      total.value = res.total;
      unreadCount.value = res.unread_count;
    } catch {
      // 后台刷新失败保留旧数据
    } finally {
      isLoading.value = false;
    }
  }

  // SSE 帧：同步未读数；latest_id 增大 = 有新消息 → 刷新列表并对
  // error 级新消息弹 toast（跳过登录后的第一帧，避免为历史积压刷屏）。
  watch(notificationData, (frame) => {
    if (!frame) return;
    unreadCount.value = frame.unread_count;
    const isFirstFrame = lastLatestId === null;
    const hasNew = !isFirstFrame && frame.latest_id > (lastLatestId as number);
    lastLatestId = frame.latest_id;
    if (hasNew) {
      fetchMessages().then(() => {
        const head = messages.value[0];
        if (head && !head.read && head.severity === 'error') {
          message.error(titleOf(head));
        }
      });
    } else if (panelOpen.value && !isFirstFrame) {
      // 其它端的已读/删除操作也让打开中的面板保持同步
      fetchMessages();
    }
  });

  // SSE 断开时的回退：30s 轮询一次未读数（静默）。
  async function pollUnread() {
    if (sseConnected.value || document.hidden || !isLoggedIn.value) return;
    try {
      unreadCount.value = await apiNotification.getUnreadCount();
    } catch {
      // Silent poll — keep the last count on a transient failure.
    }
  }

  const { pause: offPoll, resume: onPoll } = useIntervalFn(pollUnread, 30000, {
    immediate: false,
    immediateCallback: true,
  });

  watch(
    isLoggedIn,
    (loggedIn) => {
      if (loggedIn) {
        onPoll();
      } else {
        offPoll();
        messages.value = [];
        total.value = 0;
        unreadCount.value = 0;
        lastLatestId = null;
      }
    },
    { immediate: true }
  );

  async function markRead(id: number) {
    const target = messages.value.find((m) => m.id === id);
    if (!target || target.read) return;
    try {
      await apiNotification.markRead(id);
      target.read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    } catch {
      // 失败保持原状，下一次 SSE 帧会校正
    }
  }

  async function markAllRead() {
    try {
      await apiNotification.markAllRead();
      messages.value.forEach((m) => {
        m.read = true;
      });
      unreadCount.value = 0;
    } catch {
      // 同上
    }
  }

  async function remove(id: number) {
    try {
      await apiNotification.removeMessage(id);
      const target = messages.value.find((m) => m.id === id);
      messages.value = messages.value.filter((m) => m.id !== id);
      total.value = Math.max(0, total.value - 1);
      if (target && !target.read) {
        unreadCount.value = Math.max(0, unreadCount.value - 1);
      }
    } catch {
      // 同上
    }
  }

  async function clearAll() {
    try {
      await apiNotification.clearAll();
      messages.value = [];
      total.value = 0;
      unreadCount.value = 0;
    } catch {
      // 同上
    }
  }

  return {
    messages,
    total,
    unreadCount,
    isLoading,
    panelOpen,
    fetchMessages,
    markRead,
    markAllRead,
    remove,
    clearAll,
    titleOf,
    bodyOf,
  };
});
