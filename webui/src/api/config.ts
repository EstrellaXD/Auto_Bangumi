import type { Config } from '#/config';
import type { UniversalResponse } from '#/message';

export const apiConfig = {
  /**
   * 获取 config 数据
   */
  async getConfig() {
    const { data } = await axios.get<Config>('api/v1/config/get');
    return data;
  },

  /**
   * 更新 config 数据
   * @param newConfig - 需要更新的 config
   */
  async updateConfig(newConfig: Config) {
    const { data } = await axios.patch<UniversalResponse>(
      'api/v1/config/update',
      newConfig
    );
    return data;
  },
};
