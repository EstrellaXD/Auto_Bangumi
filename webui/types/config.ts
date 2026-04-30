import type { TupleToUnion } from './utils';

/** 涓嬭浇鏂瑰紡 */
export type DownloaderType = ['qbittorrent'];
/** rss parser 璇█ */
export type RssParserLang = ['zh', 'en', 'jp'];
/** 閲嶅懡鍚嶆柟寮?*/
export type RenameMethod = ['normal', 'pn', 'advance', 'none'];
/** 浠ｇ悊绫诲瀷 */
export type ProxyType = ['http', 'https', 'socks5'];
/** 閫氱煡绫诲瀷 */
export type NotificationType = [
  'telegram',
  'discord',
  'bark',
  'server-chan',
  'wecom',
  'gotify',
  'pushover',
  'webhook',
  'onebot',
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
  filter: Array<string>;
  language: TupleToUnion<RssParserLang>;
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
  message_type?: string;
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

/** Access control for the login endpoint and MCP server.
 *  Whitelist entries are IPv4/IPv6 CIDR strings (e.g. "192.168.0.0/16").
 *  An empty login_whitelist allows all IPs; an empty mcp_whitelist denies all IP-based MCP access.
 */
export interface Security {
  login_whitelist: string[];
  login_tokens: string[];
  mcp_whitelist: string[];
  mcp_tokens: string[];
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
  security: Security;
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
    filter: [],
    language: 'zh',
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
  security: {
    login_whitelist: [],
    login_tokens: [],
    mcp_whitelist: [],
    mcp_tokens: [],
  },
};

