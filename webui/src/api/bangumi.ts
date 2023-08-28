import type { BangumiRule, BangumiUpdate } from '#/bangumi';
import type { ApiSuccess } from '#/api';
import {forEach} from "lodash";


export const apiBangumi = {
  /**
   * 获取所有 bangumi 数据
   * @returns 所有 bangumi 数据
   */
  async getAll() {
    const { data } = await axios.get<BangumiRule[]>('api/v1/bangumi/get/all');
    forEach(data, (item) => {
        item.rss_link = item.rss_link.split(',');
        item.filter = item.filter.split(',');
    });
    return data;
  },

  /**
   * 获取指定 bangumiId 的规则
   * @param bangumiId  bangumi id
   * @returns 指定 bangumi 的规则
   */
  async getRule(bangumiId: number) {
    const { data } = await axios.get<BangumiRule>(
      `api/v1/bangumi/get/${bangumiId}`
    );
    data.rss_link = data.rss_link.split(',');
    data.filter = data.filter.split(',');
    return data;
  },

  /**
   * 更新指定 bangumiId 的规则
   * @param bangumiId - 需要更新的 bangumi 的 id
   * @param bangumiRule
   * @returns axios 请求返回的数据
   */
  async updateRule(bangumiId: number, bangumiRule: BangumiRule) {
    const rule = omit(bangumiRule, ['id']);
    rule.rss_link = rule.rss_link.join(',');
    rule.filter = rule.filter.join(',');
    const { data } = await axios.patch< ApiSuccess >(
      `api/v1/bangumi/update/${bangumiId}`,
      rule
    );
    return data;
  },

  /**
   * 删除指定 bangumiId 的数据库规则，会在重新匹配到后重建
   * @param bangumiId - 需要删除的 bangumi 的 id
   * @param file - 是否同时删除关联文件。
   * @returns axios 请求返回的数据
   */
  async deleteRule(bangumiId: number | number[], file: boolean) {
    let url = 'api/v1/bangumi/delete';
    let ids: undefined | number[];

    if (typeof bangumiId === 'number') {
      url = `${url}/${bangumiId}`;
    } else {
      url = `${url}/many`;
      ids = bangumiId;
    }

    const { data } = await axios.delete< ApiSuccess >(url, {
      data: ids,
      params: {
        file,
      },
    });
    return data;
  },

  /**
   * 删除指定 bangumiId 的规则。如果 file 为 true，则同时删除关联文件。
   * @param bangumiId - 需要删除规则的 bangumi 的 id。
   * @param file - 是否同时删除关联文件。
   * @returns axios 请求返回的数据
   */
  async disableRule(bangumiId: number | number[], file: boolean) {
    let url = 'api/v1/bangumi/disable';
    let ids: undefined | number[];

    if (typeof bangumiId === 'number') {
      url = `${url}/${bangumiId}`;
    } else {
      url = `${url}/many`;
      ids = bangumiId;
    }

    const { data } = await axios.delete< ApiSuccess >(url, {
      data: ids,
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
    const { data } = await axios.get< ApiSuccess >(
      `api/v1/bangumi/enable/${bangumiId}`
    );
    return data;
  },

  /**
   * 重置所有 bangumi 数据
   */
  async resetAll() {
    const { data } = await axios.get< ApiSuccess >('api/v1/bangumi/resetAll');
    return data;
  },
};
