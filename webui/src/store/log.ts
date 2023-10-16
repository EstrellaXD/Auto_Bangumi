export const useLogStore = defineStore('log', () => {
  const log = ref('');
  const { isLoggedin } = useAuth();
  const message = useMessage();

  function get() {
    const { execute, onResult } = useApi(apiLog.getLog);

    onResult((value) => {
      log.value = value;
    });

    execute();
  }

  const { execute: reset, onResult: onClearLogResult } = useApi(
    apiLog.clearLog
  );

  onClearLogResult((res) => {
    if (res) {
      log.value = '';
    }
  });

  const { pause: offUpdate, resume: onUpdate } = useIntervalFn(get, 3000, {
    immediate: false,
    immediateCallback: true,
  });

  function copy() {
    const { copy: copyLog, isSupported } = useClipboard({ source: log });
    if (isSupported) {
      copyLog();
      message.success('Copy Success!');
    } else {
      message.error('Your browser does not support Clipboard API!');
    }
  }

  return {
    log,
    get,
    reset,
    onUpdate,
    offUpdate,
    copy,
  };
});
