/**
 * @type `Bangumi` in backend/src/module/models/bangumi.py
 */
export interface BangumiRule {
  added: boolean;
  deleted: boolean;
  archived: boolean;
  dpi: string;
  eps_collect: boolean;
  filter: string[];
  group_name: string;
  id: number;
  official_title: string;
  episode_offset: number;
  season_offset: number;
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
  air_weekday: number | null; // 0=Mon, 1=Tue, ..., 6=Sun, null=Unknown
  needs_review: boolean;
  needs_review_reason: string | null;
}

export interface BangumiAPI extends Omit<BangumiRule, 'filter' | 'rss_link'> {
  filter: string;
  rss_link: string;
}

export interface SearchResult {
  order: number;
  value: BangumiRule;
}

export type BangumiUpdate = Omit<BangumiAPI, 'id'>;

export const ruleTemplate: BangumiRule = {
  added: false,
  deleted: false,
  archived: false,
  dpi: '',
  eps_collect: false,
  filter: [],
  group_name: '',
  id: 0,
  official_title: '',
  episode_offset: 0,
  season_offset: 0,
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
  air_weekday: null,
  needs_review: false,
  needs_review_reason: null,
};

/** Legacy offset suggestion (for backward compatibility) */
export interface OffsetSuggestion {
  suggested_offset: number;
  reason: string;
}

/** TMDB summary for display in offset dialog */
export interface TMDBSummary {
  title: string;
  total_seasons: number;
  season_episode_counts: Record<number, number>;
  status: string | null;
}

/** Detailed offset suggestion from detector */
export interface OffsetSuggestionDetail {
  season_offset: number;
  episode_offset: number;
  reason: string;
  confidence: 'high' | 'medium' | 'low';
}

/** Request for detect-offset API */
export interface DetectOffsetRequest {
  title: string;
  parsed_season: number;
  parsed_episode: number;
}

/** Response from detect-offset API */
export interface DetectOffsetResponse {
  has_mismatch: boolean;
  suggestion: OffsetSuggestionDetail | null;
  tmdb_info: TMDBSummary | null;
}
