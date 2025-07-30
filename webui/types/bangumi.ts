/**
 * @type `Bangumi` in backend/src/module/models/bangumi.py
 */
export interface BangumiRule {
  added: boolean;
  deleted: boolean;
  dpi: string;
  eps_collect: boolean;
  exclude_filter: string[];
  include_filter: string[];
  group_name: string;
  id: number;
  official_title: string;
  offset: number;
  poster_link: string | null;
  rss_link: string[];
  rule_name: string;
  save_path: string;
  season: number;
  season_raw: string;
  source: string | null;
  subtitle: string;
  title_raw: string;
  year: string | null;
}

export interface BangumiAPI extends Omit<BangumiRule, 'exclude_filter' | 'include_filter' | 'rss_link'> {
  exclude_filter: string;
  include_filter: string;
  rss_link: string;
}

export interface SearchResult {
  order: number;
  value: BangumiRule;
}

// export type BangumiUpdate = Omit<BangumiAPI, 'id'>;
export type BangumiUpdate = BangumiAPI

export const ruleTemplate: BangumiRule = {
  added: false,
  deleted: false,
  dpi: '',
  eps_collect: false,
  exclude_filter: [],
  include_filter: [],
  group_name: '',
  id: 0,
  official_title: '',
  offset: 0,
  poster_link: '',
  rss_link: [],
  rule_name: '',
  save_path: '',
  season: 1,
  season_raw: '',
  source: null,
  subtitle: '',
  title_raw: '',
  year: null,
};
