import { type Config, initConfig } from '#/config';
import { dirtyConfigGroups } from '@/utils/config-diff';

export const useConfigStore = defineStore('config', () => {
  const config = ref<Config>(initConfig);
  // 最近一次从服务端加载/成功保存的快照，用于脏值比对
  const savedConfig = ref<Config>(initConfig);
  const lastSaveError = ref<unknown>(null);

  const dirtyGroups = computed(() =>
    dirtyConfigGroups(savedConfig.value, config.value)
  );
  const isDirty = computed(() => dirtyGroups.value.length > 0);

  function snapshot() {
    savedConfig.value = JSON.parse(JSON.stringify(config.value));
  }

  async function getConfig() {
    const res = await apiConfig.getConfig();
    config.value = res;
    snapshot();
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
    if (result.ok) {
      snapshot();
    }
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
    dirtyGroups,
    isDirty,
    getConfig,
    setConfig,
    getSettingGroup,
  };
});
