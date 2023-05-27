export const useProgramStore = defineStore('program', () => {
  const message = useMessage();
  const { auth } = useAuth();
  const running = ref(false);
  const timer = ref<NodeJS.Timer | null>(null);

  const getStatus = async () => {
    if (auth.value !== '') {
      running.value = await apiProgram.status();
    }
  };

  const onUpdate = () => {
    getStatus();
    timer.value = setInterval(() => getStatus(), 3000);
  };

  const offUpdate = () => {
    clearInterval(Number(timer.value));
    timer.value = null;
  };

  function handleMessage(handle: string, success: boolean) {
    if (success) {
      message.success(`${handle} Success!`);
    } else {
      message.error(`${handle} Failed!`);
    }
  }

  const start = async () => {
    const res = await apiProgram.start();
    handleMessage('Start', res);
  };

  const pause = async () => {
    const res = await apiProgram.stop();
    handleMessage('Pause', res);
  };

  const shutdown = async () => {
    const res = await apiProgram.shutdown();
    handleMessage('Shutdown', res);
  };

  const restart = async () => {
    const res = await apiProgram.restart();
    handleMessage('Restart', res);
  };

  return {
    running,
    getStatus,
    onUpdate,
    offUpdate,

    start,
    pause,
    shutdown,
    restart,
  };
});
