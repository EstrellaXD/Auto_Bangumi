export interface BangumiItem {
  id: number;
  official_title: string;
  year: string | null;
  title_raw: string;
  season: number;
  season_raw: string;
  group_name: string;
  dpi: string;
  source: string;
  subtitle: string;
  eps_collect: boolean;
  offset: number;
  filter: string[];
  rss_link: string[];
  poster_link: string;
  added: boolean;
}
