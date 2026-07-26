import { createSharedComposable, useIntervalFn } from '@vueuse/core';

export const useAppInfo = createSharedComposable(() => {
  const { isLoggedIn } = useAuth();
  const { connected: sseConnected, statusData } = useEventStream();
  const running = ref<boolean>(false);
  const version = ref<string>('');
  const statusKnown = ref(false);

  // SSE 已连接时使用推送数据；否则回退到轮询。
  watch(statusData, (data) => {
    if (!data) return;
    running.value = data.status;
    version.value = data.version;
    statusKnown.value = true;
  });

  watch(isLoggedIn, (loggedIn) => {
    if (loggedIn) return;
    running.value = false;
    version.value = '';
    statusKnown.value = false;
  });

  function getStatus() {
    // SSE 已接管状态推送，或页面不可见时，跳过本次轮询请求。
    if (sseConnected.value || document.hidden) return;
    if (isLoggedIn.value) {
      apiProgram
        .status()
        .then((res) => {
          running.value = res.status;
          version.value = res.version;
          statusKnown.value = true;
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
    statusKnown,

    onUpdate,
    offUpdate,
  };
});
