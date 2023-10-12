export const useNotificationStore = defineStore('notification', () => {
  const { auth } = useAuth();
  const message = useMessage();

  const setReadLoading = ref(false);

  function setRead(message_ids: string[]) {
    const { isLoading, execute, onResult, onError } = useApi(
      apiNotification.setRead,
      {}
    );

    setReadLoading.value = isLoading.value;

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

  return {
    setRead,
    setReadLoading,
  };
});
