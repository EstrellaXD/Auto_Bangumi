import axios from 'axios';
import type { BangumiItem } from '#/bangumi';

export const apiBangumi = {
  /**
   * 获取所有 bangumi 数据
   * @returns 所有 bangumi 数据
   */
  async getAll() {
    const { data } = await axios.get<BangumiItem[]>('api/v1/bangumi/getAll');

    return data;
  },

  /**
   * 获取指定 bangumiId 的数据
   * @param bangumiId 需要获取数据的 bangumi 的 id
   * @returns 获取指定 bangumi 的数据
   */
  async getData(bangumiId: number) {
    const { data } = await axios.get<BangumiItem>(
      `api/v1/bangumi/getData/${bangumiId}`
    );

    return data;
  },

  /**
   * 更新指定 bangumiId 的数据
   * @param bangumiData - 需要更新的数据
   * @returns axios 请求返回的数据
   */
  async updateData(bangumiData: BangumiItem) {
    const { data } = await axios.post('api/v1/bangumi/updateData', bangumiData);
    return data;
  },

  /**
   * 删除指定 bangumiId 的数据
   * @param bangumiId - 需要删除的 bangumi 的 id
   * @returns axios 请求返回的数据
   */
  async deleteData(bangumiId: number) {
    const { data } = await axios.delete(
      `api/v1/bangumi/deleteData/${bangumiId}`
    );
    return data;
  },

  /**
   * 删除指定 bangumiId 的规则。如果 file 为 true，则同时删除关联文件。
   * @param bangumiId - 需要删除规则的 bangumi 的 id。
   * @param file - 是否同时删除关联文件。
   * @returns axios 请求返回的数据
   */
  async deleteRule(bangumiId: number, file: boolean) {
    const { data } = await axios.delete(
      `api/v1/bangumi/deleteRule/${bangumiId}`,
      {
        params: {
          file,
        },
      }
    );
    return data;
  },

  /**
   * 重置所有 bangumi 数据
   */
  async resetAll() {
    const { data } = await axios.post('api/v1/bangumi/resetAll');
    return data;
  },
};
