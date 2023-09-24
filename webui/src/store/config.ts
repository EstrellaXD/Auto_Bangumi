import { type Config, initConfig } from '#/config';

export const useConfigStore = defineStore('config', () => {
  const config = ref<Config>(initConfig);

  const { execute: getConfig, onResult: onGetConfigRusult } = useApi(
    apiConfig.getConfig
  );

  onGetConfigRusult((res) => {
    config.value = res;
  });

  const { execute: set, onResult: onSetRusult } = useApi(
    apiConfig.updateConfig,
    {
      failRule: (res) => !res,
      message: {
        success: 'Apply Success!',
        fail: 'Apply Failed!',
      },
    }
  );

  /**
   * 保持 config 后重启，以应用最新配置
   */
  onSetRusult(() => {
    const { restart } = useProgramStore();
    restart();
  });

  const setConfig = () => {
    set(config.value);
  };

  function getSettingGroup<Tkey extends keyof Config>(key: Tkey) {
    return computed<Config[Tkey]>({
      get() {
        return config.value[key];
      },
      set(newVal) {
        config.value[key] = newVal;
      },
    });
  }

  return {
    config,
    getConfig,
    setConfig,
    getSettingGroup,
  };
});
