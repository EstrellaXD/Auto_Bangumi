import type { TupleToUnion } from './utils';

/** 下载方式 */
export type DownloaderType = ['qbittorrent'];
/** rss parser 源 */
export type RssParserType = ['mikan'];
/** rss parser 方法 */
export type RssParserMethodType = ['tmdb', 'mikan', 'parser'];
/** rss parser 语言 */
export type RssParserLang = ['zh', 'en', 'jp'];
/** 重命名方式 */
export type RenameMethod = ['normal', 'pn', 'advance', 'none'];
/** 代理类型 */
export type ProxyType = ['http', 'https', 'socks5'];
/** 通知类型 */
export type NotificationType = [
  'telegram',
  'discord',
  'bark',
  'server-chan',
  'wecom',
  'gotify',
  'pushover',
  'webhook',
];
/** OpenAI Model List */
export type OpenAIModel = ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'];
/** OpenAI API Type */
export type OpenAIType = ['openai', 'azure'];

export interface Program {
  rss_time: number;
  rename_time: number;
  webui_port: number;
}

export interface Downloader {
  type: TupleToUnion<DownloaderType>;
  host: string;
  username: string;
  password: string;
  path: string;
  ssl: boolean;
}
export interface RssParser {
  enable: boolean;
  type: TupleToUnion<RssParserType>;
  token: string;
  custom_url: string;
  filter: Array<string>;
  language: TupleToUnion<RssParserLang>;
  parser_type: TupleToUnion<RssParserMethodType>;
}
export interface BangumiManage {
  enable: boolean;
  eps_complete: boolean;
  rename_method: TupleToUnion<RenameMethod>;
  group_tag: boolean;
  remove_bad_torrent: boolean;
}
export interface Log {
  debug_enable: boolean;
}
export interface Proxy {
  enable: boolean;
  type: TupleToUnion<ProxyType>;
  host: string;
  port: number;
  username: string;
  password: string;
}
/** Notification provider configuration */
export interface NotificationProviderConfig {
  type: TupleToUnion<NotificationType>;
  enabled: boolean;
  // Common fields
  token?: string;
  chat_id?: string;
  // Provider-specific fields
  webhook_url?: string;
  server_url?: string;
  device_key?: string;
  user_key?: string;
  api_token?: string;
  template?: string;
  url?: string;
}

export interface Notification {
  enable: boolean;
  providers: NotificationProviderConfig[];
  // Legacy fields (deprecated, for backward compatibility)
  type?: 'telegram' | 'server-chan' | 'bark' | 'wecom';
  token?: string;
  chat_id?: string;
}
export interface ExperimentalOpenAI {
  enable: boolean;
  api_key: string;
  api_base: string;
  model: TupleToUnion<OpenAIModel>;
  // azure
  api_type: TupleToUnion<OpenAIType>;
  api_version?: string;
  deployment_id?: string;
}

export interface Config {
  program: Program;
  downloader: Downloader;
  rss_parser: RssParser;
  bangumi_manage: BangumiManage;
  log: Log;
  proxy: Proxy;
  notification: Notification;
  experimental_openai: ExperimentalOpenAI;
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
    providers: [],
  },
  experimental_openai: {
    enable: false,
    api_key: '',
    api_base: 'https://api.openai.com/v1/',
    model: 'gpt-3.5-turbo',
    // azure
    api_type: 'openai',
    api_version: '2020-05-03',
    deployment_id: '',
  },
};
