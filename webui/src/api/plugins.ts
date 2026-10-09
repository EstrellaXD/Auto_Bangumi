import type { PluginUiSlot } from '@autobangumi/plugin-ui';
import type { CatalogEntry, PluginProviders, PluginsOverview } from '#/plugins';

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

  /** 签名目录；目录不可达（502）由调用方在页面内提示，不弹全局 toast */
  async catalog() {
    const { data } = await axios.get<CatalogEntry[]>('api/v1/plugins/catalog', {
      silent: true,
    });
    return data;
  },

  /** 从签名目录安装或升级插件，后端安装后即启用；version 不符时后端拒绝 */
  async install(id: string, version: string) {
    const { data } = await axios.post<PluginsOverview>(
      `api/v1/plugins/${encodeURIComponent(id)}/install`,
      null,
      { params: { version } }
    );
    return data;
  },

  /** 卸载经签名目录安装的插件（后端拒绝内置、本地、pip 与 LLM 插件） */
  async uninstall(id: string) {
    const { data } = await axios.delete<PluginsOverview>(
      `api/v1/plugins/${encodeURIComponent(id)}`
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
