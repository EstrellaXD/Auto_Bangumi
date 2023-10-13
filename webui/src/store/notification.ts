import type { NotificationData } from '#/notification';

export const useNotificationStore = defineStore('notification', () => {
  const { auth } = useAuth();
  const message = useMessage();
  const total = ref(0);
  const top10Notifications = ref<NotificationData[]>([]);
  const notifications = ref<NotificationData[]>([]);

  function setRead(message_ids: string[]) {
    const { execute, onResult, onError } = useApi(apiNotification.setRead, {});

    onResult((_) => {
      message.success(`已标记 ${message_ids.length} 条消息`);
    });

    onError((err) => {
      message.error(err.message);
    });

    if (auth.value !== '') {
      execute({ message_ids });
    }
  }

  function sendTestNotificaiton(content: string) {
    const { execute, onResult, onError } = useApi(apiNotification.send, {});

    onResult((_) => {
      message.success(`已发送测试消息`);
    });

    onError((err) => {
      message.error(err.message);
    });

    if (auth.value !== '') {
      execute({ content });
    }
  }

  function getTotal() {
    const { execute, onResult } = useApi(apiNotification.getTotal, {});

    onResult((res) => {
      total.value = res.data.total;
    });
    if (auth.value !== '') {
      execute();
    }
  }

  function getTop10Notification() {
    const { execute, onResult } = useApi(apiNotification.get, {});

    onResult((res) => {
      top10Notifications.value = res.data.messages.map((item) => {
        const { content } = JSON.parse(item.data);
        const value = {
          id: item.message_id,
          title: 'AutoBangumi',
          has_read: Boolean(item.has_read),
          datetime: `${item.datetime}`,
          content,
        };
        return value;
      });
    });

    if (auth.value !== '') {
      execute({ page: 1, limit: 10 });
    }
  }

  const { pause: offUpdate, resume: onUpdate } = useIntervalFn(
    () => {
      getTotal();
      getTop10Notification();
    },
    10000,
    {
      immediate: false,
      immediateCallback: true,
    }
  );

  function getNotification({
    page = 1,
    limit = 10,
  }: {
    page: number;
    limit: number;
  }) {
    const { execute, onResult } = useApi(apiNotification.get, {});

    onResult((res) => {
      notifications.value = res.data.messages.map((item) => {
        const { content } = JSON.parse(item.data);
        const value = {
          id: item.message_id,
          title: 'AutoBangumi',
          datetime: `${item.datetime}`,
          content,
        };
        return value;
      });
    });

    if (auth.value !== '') {
      execute({ page, limit });
    }
  }

  return {
    // for notification icon
    onUpdate,
    offUpdate,
    getTotal,
    getTop10Notification,
    // notification CRUD
    setRead,
    sendTestNotificaiton,
    getNotification,
    // refs
    total,
    top10Notifications,
    notifications,
  };
});
