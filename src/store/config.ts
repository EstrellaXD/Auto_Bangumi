import { ElMessage, ElMessageBox } from 'element-plus';
import { getConfig, setConfig } from '@/api/config';
import { appRestart } from '@/api/program';
import type { Config } from '#/config';

const { status } = storeToRefs(programStore());

export const configStore = defineStore('config', () => {
  const config = ref<Config>();

  const get = async () => {
    config.value = await getConfig();
  };

  const set = async (newConfig: Omit<Config, 'data_version'>) => {
    let finalConfig: Config;
    if (config.value !== undefined) {
      finalConfig = Object.assign(config.value, newConfig);
      const res = await setConfig(finalConfig);

      if (res) {
        ElMessage({
          message: '保存成功！',
          type: 'success',
        });

        if (!status.value) {
          ElMessageBox.confirm('当前程序没有运行，是否重启?', {
            type: 'warning',
          })
            .then(() => {
              appRestart()
                .then((res) => {
                  if (res) {
                    ElMessage({
                      message: '正在重启, 请稍后刷新页面...',
                      type: 'success',
                    });
                  }
                })
                .catch((error) => {
                  console.error(
                    '🚀 ~ file: index.vue:41 ~ .then ~ error:',
                    error
                  );
                  ElMessage({
                    message: '操作失败, 请手动重启容器!',
                    type: 'error',
                  });
                });
            })
            .catch(() => {});
        }
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
