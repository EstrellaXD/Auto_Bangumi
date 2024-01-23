import type { NotificationData, WithTotalAndMessages } from '#/notification';

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
      total.value = res.data?.total ?? 0;
    });
    if (auth.value !== '') {
      execute();
    }
  }

  function getTop10Notification() {
    const { execute, onResult } = useApi(apiNotification.get, {});

    onResult((res) => {
      top10Notifications.value = (res.data as WithTotalAndMessages).messages;
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
      notifications.value = (res.data as WithTotalAndMessages).messages.map(
        (item) => {
          // make sure field order is correct.
          return {
            id: item.id,
            title: item.title,
            datetime: item.datetime,
            content: item.content,
            has_read: item.has_read,
          };
        }
      );
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
