import type { PluginUiSlot } from '@autobangumi/plugin-ui';
import type { PluginProviders, PluginsOverview } from '#/plugins';

export const apiPlugins = {
  /** 已发现的插件、状态、配置 schema 与（掩码后的）当前配置 */
  async list() {
    const { data } = await axios.get<PluginsOverview>('api/v1/plugins');
    return data;
  },

  /** 启用/停用插件或修改配置；后端保存后立即重新应用 */
  async update(
    id: string,
    body: { enabled?: boolean; options?: Record<string, unknown> }
  ) {
    const { data } = await axios.put<PluginsOverview>(
      `api/v1/plugins/${encodeURIComponent(id)}`,
      body
    );
    return data;
  },

  async updateSettings(allowUnsigned: boolean) {
    const { data } = await axios.put<PluginsOverview>(
      'api/v1/plugins/settings',
      { allow_unsigned: allowUnsigned }
    );
    return data;
  },

  /** 已启用插件声明的前端挂载点 */
  async ui() {
    const { data } = await axios.get<PluginUiSlot[]>('api/v1/plugins/ui');
    return data;
  },

  /** 插件提供的下载器 / 通知渠道 / 搜索站点 id */
  async providers() {
    const { data } = await axios.get<PluginProviders>(
      'api/v1/plugins/providers'
    );
    return data;
  },
};
