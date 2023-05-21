export const useLogStore = defineStore('log', () => {
  const log = ref('');
  const timer = ref<NodeJS.Timer | null>(null);

  const get = async () => {
    log.value = await apiLog.getLog();
  };

  const onUpdate = () => {
    get();
    timer.value = setInterval(() => get(), 3000);
  };

  const removeUpdate = () => {
    clearInterval(Number(timer.value));
  };

  return {
    log,
    get,
    onUpdate,
    removeUpdate,
  };
});
