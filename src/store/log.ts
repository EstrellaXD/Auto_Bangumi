import { getABLog } from '../api/debug';

export const logStore = defineStore('log', () => {
  const log = ref('');
  const timer = ref<NodeJS.Timer | null>(null);

  const get = async () => {
    log.value = await getABLog();
  };

  const onUpdate = () => {
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
