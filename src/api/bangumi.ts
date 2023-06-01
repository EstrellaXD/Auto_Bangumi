import type { BangumiRule } from '#/bangumi';

export const apiBangumi = {
  /**
   * 获取所有 bangumi 数据
   * @returns 所有 bangumi 数据
   */
  async getAll() {
    const { data } = await axios.get<BangumiRule[]>('api/v1/bangumi/getAll');

    return data;
  },

  /**
   * 获取指定 bangumiId 的规则
   * @param bangumiId  bangumi id
   * @returns 指定 bangumi 的规则
   */
  async getRule(bangumiId: number) {
    const { data } = await axios.get<BangumiRule>(
      `api/v1/bangumi/getRule/${bangumiId}`
    );

    return data;
  },

  /**
   * 更新指定 bangumiId 的规则
   * @param bangumiData - 需要更新的规则
   * @returns axios 请求返回的数据
   */
  async updateRule(bangumiRule: BangumiRule) {
    const { data } = await axios.post<{
      msg: string;
      status: 'success';
    }>('api/v1/bangumi/updateRule', bangumiRule);
    return data;
  },

  /**
   * 删除指定 bangumiId 的数据库规则，会在重新匹配到后重建
   * @param bangumiId - 需要删除的 bangumi 的 id
   * @param file - 是否同时删除关联文件。
   * @returns axios 请求返回的数据
   */
  async deleteRule(bangumiId: number, file: boolean) {
    const { data } = await axios.delete<{
      status: 'success';
      msg: string;
    }>(`api/v1/bangumi/deleteRule/${bangumiId}`);
    return data;
  },

  /**
   * 删除指定 bangumiId 的规则。如果 file 为 true，则同时删除关联文件。
   * @param bangumiId - 需要删除规则的 bangumi 的 id。
   * @param file - 是否同时删除关联文件。
   * @returns axios 请求返回的数据
   */
  async disableRule(bangumiId: number, file: boolean) {
    const { data } = await axios.delete<{
      status: 'success';
      msg: string;
    }>(`api/v1/bangumi/disableRule/${bangumiId}`, {
      params: {
        file,
      },
    });
    return data;
  },

  /**
   * 启用指定 bangumiId 的规则
   * @param bangumiId - 需要启用的 bangumi 的 id
   */
  async enableRule(bangumiId: number) {
    const { data } = await axios.get<{
      status: 'success';
      msg: string;
    }>(`api/v1/bangumi/enableRule/${bangumiId}`);
    return data;
  },

  /**
   * 重置所有 bangumi 数据
   */
  async resetAll() {
    const { data } = await axios.post<{
      status: 'ok';
    }>('api/v1/bangumi/resetAll');
    return data;
  },
};
