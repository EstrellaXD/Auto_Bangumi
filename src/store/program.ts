import { appStatus } from '../api/program';

export const programStore = defineStore('program', () => {
  const status = ref(false);
  const timer = ref<NodeJS.Timer | null>(null);

  const getStatus = async () => {
    status.value = await appStatus();
  };

  const onUpdate = () => {
    timer.value = setInterval(() => getStatus(), 3000);
  };

  return {
    status,
    getStatus,
    onUpdate,
  };
});
