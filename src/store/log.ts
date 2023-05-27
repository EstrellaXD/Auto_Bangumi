export const useLogStore = defineStore('log', () => {
  const log = ref('');
  const timer = ref<NodeJS.Timer | null>(null);
  const { auth } = useAuth();

  const get = async () => {
    if (auth.value !== '') {
      log.value = await apiLog.getLog();
    }
  };

  const onUpdate = () => {
    get();
    timer.value = setInterval(() => get(), 3000);
  };

  const offUpdate = () => {
    clearInterval(Number(timer.value));
    timer.value = null;
  };

  return {
    log,
    get,
    onUpdate,
    offUpdate,
  };
});
