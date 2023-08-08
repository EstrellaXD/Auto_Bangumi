export interface BangumiRule {
  added: boolean;
  deleted: boolean;
  dpi: string;
  eps_collect: boolean;
  filter: string[];
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

export interface BangumiUpdate {
  added: boolean;
  deleted: boolean;
  dpi: string;
  eps_collect: boolean;
  filter: string;
  group_name: string;
  official_title: string;
  offset: number;
  poster_link: string | null;
  rss_link: string;
  rule_name: string;
  save_path: string;
  season: number;
  season_raw: string;
  source: string | null;
  subtitle: string;
  title_raw: string;
  year: string | null;
}
