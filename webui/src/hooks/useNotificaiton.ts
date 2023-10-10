import type { Notification } from '#/notification';

export const useNotification = createSharedComposable(() => {
  // TODO: add auth
  // const { auth } = useAuth();
  const notifications = ref<Notification[]>([]);
  const total = ref(0);

  function getNotification() {
    const { execute, onResult } = useApi(apiNotification.get, {});

    onResult((res) => {
      total.value = res.data.total;
      notifications.value = res.data.messages.map((item, index) => {
        const { content } = JSON.parse(item.data);
        const value = {
          key: index,
          id: item.message_id,
          title: 'AutoBangumi',
          hasRead: false,
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
    execute();
  }

  const { pause: offUpdate, resume: onUpdate } = useIntervalFn(
    getNotification,
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
