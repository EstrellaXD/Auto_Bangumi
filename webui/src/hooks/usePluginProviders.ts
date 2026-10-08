import type { PluginProviders } from '#/plugins';
import { apiPlugins } from '@/api/plugins';

const providers = ref<PluginProviders>({
  downloader: [],
  notifier: [],
  search_site: [],
});
let loaded = false;

/**
 * 插件提供的下载器 / 通知渠道 / 搜索站点 id，供设置页下拉框合并候选。
 * 全局只请求一次；请求失败（如未登录）时保持空列表，不影响内置选项。
 */
export function usePluginProviders() {
  if (!loaded) {
    loaded = true;
    apiPlugins
      .providers()
      .then((data) => {
        providers.value = data;
      })
      .catch(() => {
        loaded = false;
      });
  }
  return providers;
}
