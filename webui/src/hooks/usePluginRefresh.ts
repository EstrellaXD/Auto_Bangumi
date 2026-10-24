import { refreshPluginProviders } from '@/hooks/usePluginProviders';
import { refreshPluginUi } from '@/hooks/usePluginUi';

/** 插件集合每变化一次加一；被 KeepAlive 缓存的页面再次进入时据此判断是否重新加载 */
export const pluginSetVersion = ref(0);

/**
 * 插件安装、卸载、启停或改配置后调用：同步 config store 的 plugins 段（只刷新
 * 插件卡片保存的字段，保留未保存的下载器实例与 slots 修改）、下载器/通知渠道
 * 候选与插件前端挂载点。
 */
export async function refreshPluginState() {
  pluginSetVersion.value++;
  // 改动已在服务端生效；这里的失败不算操作失败，下次加载时会再同步
  await Promise.allSettled([
    useConfigStore().refreshGroup('plugins', [
      'allow_unsigned',
      'enabled',
      'options',
    ]),
    refreshPluginProviders(),
    refreshPluginUi(),
  ]);
}
