import { ElMessage } from 'element-plus';
import { getConfig, setConfig } from '@/api/config';
import type { Config } from '#/config';

export const configStore = defineStore('config', () => {
  const config = ref<Config>();

  const get = async () => {
    config.value = await getConfig();
  };

  const set = async (newConfig: Omit<Config, 'data_version'>) => {
    let finalConfig: Config;
    if (config.value !== undefined) {
      finalConfig = Object.assign(config.value, newConfig);
      const { message } = await setConfig(finalConfig);

      if (message === 'Success') {
        ElMessage({
          message: '保存成功!',
          type: 'success',
        });
      } else {
        ElMessage({
          message: '保存失败, 请重试!',
          type: 'error',
        });
      }
    }

    return false;
  };

  return {
    get,
    set,
    config,
  };
});
