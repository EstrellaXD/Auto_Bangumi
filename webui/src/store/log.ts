import { useClipboard, useIntervalFn } from '@vueuse/core';

export const useLogStore = defineStore('log', () => {
  const message = useMessage();
  const { isLoggedIn } = useAuth();
  const { t } = useMyI18n();
  const { connected: sseConnected, logData } = useEventStream();

  const log = ref('');

  // SSE 已连接时使用推送数据；否则回退到轮询。
  watch(logData, (data) => {
    if (data === null) return;
    log.value = data;
  });

  function getLog(force = false) {
    // SSE 已接管日志推送，或页面不可见时，跳过本次轮询请求；
    // force = 用户显式点击刷新，总是拉取（SSE 只在日志变化时推送，
    // 新会话连上后可能一直收不到初始内容）。
    if (!force && (sseConnected.value || document.hidden)) return;
    if (isLoggedIn.value) {
      apiLog
        .getLog()
        .then((res) => {
          log.value = res;
        })
        .catch(() => {
          // Silent poll — keep the last log content on a transient failure.
        });
    }
  }

  const { execute: reset } = useApi(apiLog.clearLog, {
    showMessage: true,
    onSuccess() {
      log.value = '';
    },
  });

  const { pause: offUpdate, resume: onUpdate } = useIntervalFn(getLog, 10000, {
    immediate: false,
    immediateCallback: true,
  });

  watch(isLoggedIn, (loggedIn) => {
    if (!loggedIn) {
      offUpdate();
    }
  });

  const { copy: clipboardCopy, isSupported: clipboardSupported } = useClipboard(
    {
      legacy: true,
    }
  );

  function copy() {
    if (clipboardSupported.value) {
      clipboardCopy(log.value);
      message.success(t('notify.copy_success'));
    } else {
      message.error(t('notify.copy_failed'));
    }
  }

  return {
    log,
    getLog,
    reset,
    onUpdate,
    offUpdate,
    copy,
  };
});
