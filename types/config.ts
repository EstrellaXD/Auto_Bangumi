import type { UnionToTuple } from '#/utils';

export interface Config {
  program: {
    rss_time: number;
    rename_time: number;
    webui_port: number;
  };
  downloader: {
    type: 'qbittorrent';
    host: string;
    username: string;
    password: string;
    path: string;
    ssl: boolean;
  };
  rss_parser: {
    enable: boolean;
    type: 'mikan';
    token: string;
    custom_url: string;
    filter: Array<string>;
    language: 'zh' | 'en' | 'jp';
    parser_type: 'tmdb' | 'mikan' | 'parser';
  };
  bangumi_manage: {
    enable: boolean;
    eps_complete: boolean;
    rename_method: 'normal' | 'pn' | 'advance' | 'none';
    group_tag: boolean;
    remove_bad_torrent: boolean;
  };
  log: {
    debug_enable: boolean;
  };
  proxy: {
    enable: boolean;
    type: 'http' | 'https' | 'socks5';
    host: string;
    port: number;
    username: string;
    password: string;
  };
  notification: {
    enable: boolean;
    type: 'telegram' | 'server-chan' | 'bark';
    token: string;
    chat_id: string;
  };
}

export const initConfig: Config = {
  program: {
    rss_time: 0,
    rename_time: 0,
    webui_port: 0,
  },
  downloader: {
    type: 'qbittorrent',
    host: '',
    username: '',
    password: '',
    path: '',
    ssl: false,
  },
  rss_parser: {
    enable: true,
    type: 'mikan',
    token: '',
    custom_url: '',
    filter: [],
    language: 'zh',
    parser_type: 'parser',
  },
  bangumi_manage: {
    enable: true,
    eps_complete: true,
    rename_method: 'normal',
    group_tag: true,
    remove_bad_torrent: true,
  },
  log: {
    debug_enable: false,
  },
  proxy: {
    enable: false,
    type: 'http',
    host: '',
    port: 0,
    username: '',
    password: '',
  },
  notification: {
    enable: false,
    type: 'telegram',
    token: '',
    chat_id: '',
  },
};

type getItem<T extends keyof Config> = Pick<Config, T>[T];

export type Program = getItem<'program'>;
export type Downloader = getItem<'downloader'>;
export type RssParser = getItem<'rss_parser'>;
export type BangumiManage = getItem<'bangumi_manage'>;
export type Log = getItem<'log'>;
export type Proxy = getItem<'proxy'>;
export type Notification = getItem<'notification'>;

/** 下载方式 */
export type DownloaderType = UnionToTuple<Downloader['type']>;
/** rss parser 源 */
export type RssParserType = UnionToTuple<RssParser['type']>;
/** rss parser 方法 */
export type RssParserMethodType = UnionToTuple<RssParser['parser_type']>;
/** rss parser 语言 */
export type RssParserLang = UnionToTuple<RssParser['language']>;
/** 重命名方式 */
export type RenameMethod = UnionToTuple<BangumiManage['rename_method']>;
/** 代理类型 */
export type ProxyType = UnionToTuple<Proxy['type']>;
/** 通知类型 */
export type NotificationType = UnionToTuple<Notification['type']>;
