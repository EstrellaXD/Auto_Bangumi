export interface RSS {
  id: number;
  name: string;
  url: string;
  aggregate: boolean;
  parser: string;
  enabled: boolean;
  connection_status: string | null;
  last_checked_at: string | null;
  last_error: string | null;
}

export const rssTemplate: RSS = {
  id: 0,
  name: '',
  url: '',
  aggregate: false,
  parser: 'tmdb',
  enabled: false,
  connection_status: null,
  last_checked_at: null,
  last_error: null,
};

export interface RSSPreviewItem {
  name: string;
  url: string;
  homepage: string | null;
}

export interface RSSPreviewResponse {
  items: RSSPreviewItem[];
  global_filter: string[];
}
