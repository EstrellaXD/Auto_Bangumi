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
  /** 由此订阅新建的规则继承；null 为默认实例 */
  downloader_id: string | null;
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
  downloader_id: null,
};
