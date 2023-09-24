export const useProgramStore = defineStore('program', () => {
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
  const { execute: resetRule } = useApi(
    apiBangumi.resetAll,
    opts('Reset Rule')
  );

  return {
    start,
    pause,
    shutdown,
    restart,
    resetRule,
  };
});
