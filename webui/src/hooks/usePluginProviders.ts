import type { PluginProviders } from '#/plugins';
import { apiPlugins } from '@/api/plugins';

const providers = ref<PluginProviders>({
  downloader: [],
  notifier: [],
  search_site: [],
  metadata_provider: [],
  rename_strategy: [],
});
let loaded = false;

/** 重新拉取插件 Provider id；插件启停或配置变更后调用。 */
export async function refreshPluginProviders() {
  loaded = true;
  try {
    providers.value = await apiPlugins.providers();
  } catch {
    loaded = false;
  }
}

/**
 * 插件提供的下载器 / 通知渠道 / 搜索站点 / 元数据源 / 重命名方式 id，供设置页下拉框合并候选。
 * 首次使用时请求；请求失败（如未登录）时保持空列表，不影响内置选项。
 */
export function usePluginProviders() {
  if (!loaded) refreshPluginProviders();
  return providers;
}
