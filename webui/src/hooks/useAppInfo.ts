import { createSharedComposable, useIntervalFn } from '@vueuse/core';

export const useAppInfo = createSharedComposable(() => {
  const { isLoggedIn } = useAuth();
  const running = ref<boolean>(false);
  const version = ref<string>('');

  function getStatus() {
    if (isLoggedIn.value) {
      apiProgram
        .status()
        .then((res) => {
          running.value = res.status;
          version.value = res.version;
        })
        .catch(() => {
          // Errors are already surfaced (throttled) by the axios interceptor;
          // swallow here so a transient backend restart doesn't spam an
          // unhandled rejection on every 3s poll tick.
        });
    }
  }

  const { pause: offUpdate, resume: onUpdate } = useIntervalFn(
    getStatus,
    3000,
    {
      immediate: false,
      immediateCallback: true,
    }
  );

  return {
    running,
    version,

    onUpdate,
    offUpdate,
  };
});
