import { initConfig, type Config } from '#/config';

export const useConfigStore = defineStore('config', () => {
  const config = ref<Config>(initConfig);

  const { execute: getConfig, onResult: onGetConfigRusult } = useApi(
    apiConfig.getConfig
  );

  onGetConfigRusult((res) => {
    config.value = res;
  });

  const { execute: set } = useApi(apiConfig.updateConfig, {
    failRule: (res) => !res,
    message: {
      success: 'Apply Success!',
      fail: 'Apply Failed!',
    },
  });

  const setConfig = () => set(config.value);

  function getSettingGroup<Tkey extends keyof Config>(key: Tkey) {
    return computed<Config[Tkey]>(() => config.value[key]);
  }

  return {
    config,
    getConfig,
    setConfig,
    getSettingGroup,
  };
});
