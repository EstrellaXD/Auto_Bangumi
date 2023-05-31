export const useProgramStore = defineStore('program', function () {
  const { auth } = useAuth();
  const running = ref(false);

  function getStatus() {
    const { execute, onResult } = useApi(apiProgram.status);

    onResult((res) => {
      running.value = res;
    });

    if (auth.value !== '') {
      execute();
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

  function opts(handle: string) {
    return {
      failRule: (res: boolean) => !res,
      message: {
        success: `${handle} Success!`,
        fail: `${handle} Failed!`,
      },
    };
  }

  const { execute: start } = useApi(apiProgram.start, opts('Start'));
  const { execute: pause } = useApi(apiProgram.stop, opts('Pause'));
  const { execute: shutdown } = useApi(apiProgram.shutdown, opts('Shutdown'));
  const { execute: restart } = useApi(apiProgram.restart, opts('Restart'));

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
