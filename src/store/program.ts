export const programStore = defineStore('program', () => {
  const running = ref(false);
  const timer = ref<NodeJS.Timer | null>(null);

  const getStatus = async () => {
    running.value = await apiProgram.status();
  };

  const onUpdate = () => {
    getStatus();
    timer.value = setInterval(() => getStatus(), 3000);
  };

  return {
    running,
    getStatus,
    onUpdate,
  };
});
