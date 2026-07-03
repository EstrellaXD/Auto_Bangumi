import { type Config, initConfig } from '#/config';

export const useConfigStore = defineStore('config', () => {
  const config = ref<Config>(initConfig);
  const lastSaveError = ref<unknown>(null);

  async function getConfig() {
    const res = await apiConfig.getConfig();
    config.value = res;
  }

  const { execute: set } = useApi(apiConfig.updateConfig, {
    showMessage: true,
    onSuccess() {
      // 保存 config 后重启，以应用最新配置
      const { restart } = useProgramStore();
      restart();
    },
  });

  const setConfig = async () => {
    const result = await set(config.value);
    lastSaveError.value = result.ok ? null : result.error;
    return result;
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
    lastSaveError,
    getConfig,
    setConfig,
    getSettingGroup,
  };
});
