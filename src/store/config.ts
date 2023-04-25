import { defineStore } from 'pinia';
import { getConfig, setConfig } from '@/api/config';
import type { Config } from '#/config';

export const configStore = defineStore('config', () => {
  const config = ref<Config>();

  const get = async () => {
    config.value = await getConfig();
  };

  get();

  const set = (newConfig: Omit<Config, 'data_version'>) => {
    let finalConfig: Config;
    if (config.value !== undefined) {
      finalConfig = Object.assign(config.value, newConfig);
      return setConfig(finalConfig);
    }

    return false;
  };

  return {
    get,
    set,
    config,
  };
});
