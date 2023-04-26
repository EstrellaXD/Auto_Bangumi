import { defineStore } from 'pinia';
import { getABLog } from '../api/debug';

export const logStore = defineStore('log', () => {
  const log = ref('');
  const timer = ref<number | null>(null);

  const get = async () => {
    const { data } = await getABLog();
    log.value = data;
  };

  const onUpdate = () => {
    timer.value = setInterval(get, 5000);
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
