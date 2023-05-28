export const useLogStore = defineStore('log', () => {
  const log = ref('');
  const timer = ref<NodeJS.Timer | null>(null);
  const { auth } = useAuth();
  const message = useMessage();

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

  const reset = async () => {
    const res = await apiLog.clearLog();
    if (res) {
      log.value = '';
    }
  };

  const copy = () => {
    const { copy: copyLog, isSupported } = useClipboard({ source: log });
    if (isSupported) {
      copyLog();
      message.success('Copy Success!');
    } else {
      message.error('Your browser does not support Clipboard API!');
    }
  };

  return {
    log,
    get,
    reset,
    onUpdate,
    offUpdate,
    copy,
  };
});
