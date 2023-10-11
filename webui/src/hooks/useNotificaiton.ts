import type { Notification } from '#/notification';

export const useNotification = createSharedComposable(() => {
  // TODO: add auth
  // const { auth } = useAuth();

  const notifications = ref<Notification[]>([]);
  const total = ref(0);

  function getTotal() {
    const { execute, onResult } = useApi(apiNotification.getTotal, {});

    onResult((res) => {
      total.value = res.data.total;
    });
    execute();
  }

  function getNotification() {
    const { execute, onResult } = useApi(apiNotification.get, {});

    onResult((res) => {
      notifications.value = res.data.messages.map((item) => {
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

    // TODO: add auth
    // if (auth.value !== '') {
    //     execute();
    // }
    execute({ page: 1, limit: 10 });
  }

  const { pause: offUpdate, resume: onUpdate } = useIntervalFn(
    () => {
      getTotal();
      getNotification();
    },
    5000,
    {
      immediate: false,
      immediateCallback: true,
    }
  );
  return {
    total,
    notifications,

    onUpdate,
    offUpdate,
  };
});

export const useNotificationPage = createSharedComposable(() => {
  // TODO: add auth
  // const { auth } = useAuth();

  const { total } = useNotification();
  const { execute, onResult } = useApi(apiNotification.get, {});
  const notifications = ref<Notification[]>([]);
  const page = ref(1);
  const limit = ref(10);

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

  // TODO: add auth
  // if (auth.value !== '') {
  //     execute();
  // }

  watch([page, limit], () => {
    execute({ page: page.value, limit: limit.value });
  });

  execute({ page: page.value, limit: limit.value });

  return {
    total,
    page,
    limit,
    notifications,
  };
});
