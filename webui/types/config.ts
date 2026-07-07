import type { TupleToUnion } from './utils';

/** 下载方式 */
export type DownloaderType = ['qbittorrent', 'aria2'];
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
/** LLM 提供商 id（内置三家 + 预设/插件，开放集合） */
export type LLMProviderId = string;
/** 单个提供商的凭据/模型/端点覆盖 */
export interface LLMProviderOverride {
  api_key: string;
  model: string;
  base_url: string;
}
/** LLM 解析模式（fallback：正则优先；primary：LLM 优先） */
export type LLMParseMode = ['fallback', 'primary'];
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
  track_orphans: boolean;
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
/** 外部数据源地址与凭据（TMDB / bgm.tv）：镜像与自配 key */
export interface Network {
  tmdb_base_url: string;
  /** 留空回退到内置共享 key */
  tmdb_api_key: string;
  bgm_base_url: string;
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
export interface LLM {
  enable: boolean;
  provider: LLMProviderId;
  api_key: string;
  model: string;
  /** 自定义端点，仅 openai 提供商使用；空串表示官方 API */
  base_url: string;
  mode: TupleToUnion<LLMParseMode>;
  /** 单次请求超时（秒） */
  timeout: number;
  /** 解析结果缓存时长（秒），0 = 关闭 */
  cache_ttl: number;
  /** 最大并发请求数 */
  max_concurrency: number;
  /** 连续失败多少次后熔断 */
  failure_threshold: number;
  /** 熔断后暂停调用的时长（秒） */
  failure_backoff: number;
  /** 按提供商 id 存放的凭据/模型/端点覆盖 */
  providers: Record<string, LLMProviderOverride>;
}

/** @deprecated 旧版 OpenAI 解析配置，已被 LLM 段取代（保留向后兼容） */
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

/** 在线自动更新配置 */
export interface Update {
  /** 更新渠道：stable 仅稳定版；beta 含预发布版本 */
  channel: 'stable' | 'beta';
  /** 进入设置页时是否自动检查一次更新 */
  auto_check: boolean;
}

export interface Config {
  program: Program;
  downloader: Downloader;
  rss_parser: RssParser;
  bangumi_manage: BangumiManage;
  log: Log;
  proxy: Proxy;
  network: Network;
  notification: Notification;
  llm: LLM;
  /** @deprecated 已被 llm 段取代 */
  experimental_openai: ExperimentalOpenAI;
  security: Security;
  update: Update;
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
    track_orphans: true,
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
  network: {
    // 与 backend/src/module/models/config.py 的 Network 默认值保持一致
    tmdb_base_url: 'https://api.themoviedb.org',
    tmdb_api_key: '',
    bgm_base_url: 'https://api.bgm.tv',
  },
  notification: {
    enable: false,
    providers: [],
  },
  llm: {
    enable: false,
    provider: 'openai',
    api_key: '',
    model: 'gpt-5-mini',
    base_url: '',
    mode: 'fallback',
    // 与 backend/src/module/models/config.py 的 LLM 默认值保持一致
    timeout: 20,
    cache_ttl: 900,
    max_concurrency: 2,
    failure_threshold: 3,
    failure_backoff: 300,
    providers: {},
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
  update: {
    channel: 'stable',
    auto_check: true,
  },
};
