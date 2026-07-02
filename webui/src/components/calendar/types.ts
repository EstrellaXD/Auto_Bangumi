import type { BangumiRule } from '#/bangumi';

/** 按 official_title + season 分组后的番剧组，日历页面/看板/卡片共用 */
export interface BangumiGroup {
  key: string;
  primary: BangumiRule;
  rules: BangumiRule[];
}
