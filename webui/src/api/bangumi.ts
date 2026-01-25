import { omit } from 'radash';
import type {
  BangumiAPI,
  BangumiRule,
  DetectOffsetRequest,
  DetectOffsetResponse,
  OffsetSuggestion,
} from '#/bangumi';
import type { ApiSuccess } from '#/api';

export const apiBangumi = {
  /**
   * 获取所有 bangumi 数据
   * @returns 所有 bangumi 数据
   */
  async getAll() {
    const { data } = await axios.get<BangumiAPI[]>('api/v1/bangumi/get/all');
    const result: BangumiRule[] = data.map((bangumi) => ({
      ...bangumi,
      filter: bangumi.filter.split(','),
      rss_link: bangumi.rss_link.split(','),
      air_weekday: bangumi.air_weekday ?? null,
    }));
    return result;
  },

  /**
   * 获取指定 bangumiId 的规则
   * @param bangumiId  bangumi id
   * @returns 指定 bangumi 的规则
   */
  async getRule(bangumiId: number) {
    const { data } = await axios.get<BangumiAPI>(
      `api/v1/bangumi/get/${bangumiId}`
    );
    const result: BangumiRule = {
      ...data,
      filter: data.filter.split(','),
      rss_link: data.rss_link.split(','),
      air_weekday: data.air_weekday ?? null,
    };
    return result;
  },

  /**
   * 更新指定 bangumiId 的规则
   * @param bangumiId - 需要更新的 bangumi 的 id
   * @param bangumiRule
   * @returns axios 请求返回的数据
   */
  async updateRule(bangumiId: number, bangumiRule: BangumiRule) {
    const rule: BangumiAPI = {
      ...bangumiRule,
      filter: bangumiRule.filter.join(','),
      rss_link: bangumiRule.rss_link.join(','),
    };
    const post = omit(rule, ['id']);
    const { data } = await axios.patch<ApiSuccess>(
      `api/v1/bangumi/update/${bangumiId}`,
      post
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

    const { data } = await axios.delete<ApiSuccess>(url, {
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

    const { data } = await axios.delete<ApiSuccess>(url, {
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
    const { data } = await axios.get<ApiSuccess>(
      `api/v1/bangumi/enable/${bangumiId}`
    );
    return data;
  },

  /**
   * 重置所有 bangumi 数据
   */
  async resetAll() {
    const { data } = await axios.get<ApiSuccess>('api/v1/bangumi/reset/all');
    return data;
  },

  /**
   * 刷新所有没有海报的 bangumi 海报
   */
  async refreshPoster() {
    const { data } = await axios.get<ApiSuccess>(
      'api/v1/bangumi/refresh/poster/all'
    );
    return data;
  },

  /**
   * 从 Bangumi.tv 刷新放送日历数据
   */
  async refreshCalendar() {
    const { data } = await axios.get<ApiSuccess>(
      'api/v1/bangumi/refresh/calendar'
    );
    return data;
  },

  /**
   * 归档指定 bangumi
   * @param bangumiId - 需要归档的 bangumi 的 id
   */
  async archiveRule(bangumiId: number) {
    const { data } = await axios.patch<ApiSuccess>(
      `api/v1/bangumi/archive/${bangumiId}`
    );
    return data;
  },

  /**
   * 取消归档指定 bangumi
   * @param bangumiId - 需要取消归档的 bangumi 的 id
   */
  async unarchiveRule(bangumiId: number) {
    const { data } = await axios.patch<ApiSuccess>(
      `api/v1/bangumi/unarchive/${bangumiId}`
    );
    return data;
  },

  /**
   * 刷新 TMDB 元数据并自动归档已完结番剧
   */
  async refreshMetadata() {
    const { data } = await axios.get<ApiSuccess>(
      'api/v1/bangumi/refresh/metadata'
    );
    return data;
  },

  /**
   * 获取自动检测的剧集偏移量建议
   * @param bangumiId - bangumi 的 id
   */
  async suggestOffset(bangumiId: number) {
    const { data } = await axios.get<OffsetSuggestion>(
      `api/v1/bangumi/suggest-offset/${bangumiId}`
    );
    return data;
  },

  /**
   * 检测季度/集数与 TMDB 的不匹配
   * @param request - 包含标题、解析的季度和集数
   */
  async detectOffset(request: DetectOffsetRequest) {
    const { data } = await axios.post<DetectOffsetResponse>(
      'api/v1/bangumi/detect-offset',
      request
    );
    return data;
  },

  /**
   * 清除 bangumi 的需要检查标记
   * @param bangumiId - bangumi 的 id
   */
  async dismissReview(bangumiId: number) {
    const { data } = await axios.post<ApiSuccess>(
      `api/v1/bangumi/dismiss-review/${bangumiId}`
    );
    return data;
  },

  /**
   * 获取所有需要检查偏移量的 bangumi
   */
  async getNeedsReview() {
    const { data } = await axios.get<BangumiAPI[]>(
      'api/v1/bangumi/needs-review'
    );
    return data.map((bangumi) => ({
      ...bangumi,
      filter: bangumi.filter.split(','),
      rss_link: bangumi.rss_link.split(','),
      air_weekday: bangumi.air_weekday ?? null,
    })) as BangumiRule[];
  },
};
