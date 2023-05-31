import type { Config } from '#/config';

export const apiConfig = {
  /**
   * 获取 config 数据
   */
  async getConfig() {
    const { data } = await axios.get<Config>('api/v1/getConfig');
    return data;
  },

  /**
   * 更新 config 数据
   * @param newConfig - 需要更新的 config
   */
  async updateConfig(newConfig: Config) {
    const { data } = await axios.post<{
      message: 'Success' | 'Failed to update config';
    }>('api/v1/updateConfig', newConfig);

    return data.message === 'Success';
  },
};
