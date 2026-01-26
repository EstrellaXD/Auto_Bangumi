/**
 * Mock API responses for testing
 */

import type { BangumiAPI, BangumiRule } from '#/bangumi';
import type { RSS } from '#/rss';
import type { ApiSuccess } from '#/api';
import type { LoginSuccess } from '#/auth';

// ============================================================================
// Auth Mocks
// ============================================================================

export const mockLoginSuccess: LoginSuccess = {
  access_token: 'mock_access_token_123',
  token_type: 'bearer',
  expire: Date.now() + 86400000, // 24 hours from now
};

export const mockApiSuccess: ApiSuccess = {
  msg_en: 'Success',
  msg_zh: '成功',
};

// ============================================================================
// Bangumi Mocks
// ============================================================================

export const mockBangumiAPI: BangumiAPI = {
  id: 1,
  official_title: 'Test Anime',
  year: '2024',
  title_raw: '[TestGroup] Test Anime',
  season: 1,
  season_raw: '',
  group_name: 'TestGroup',
  dpi: '1080p',
  source: 'Web',
  subtitle: 'CHT',
  eps_collect: false,
  episode_offset: 0,
  season_offset: 0,
  filter: '720',
  rss_link: 'https://mikanani.me/RSS/test',
  poster_link: '/posters/test.jpg',
  added: true,
  rule_name: '[TestGroup] Test Anime S1',
  save_path: '/downloads/Bangumi/Test Anime (2024)/Season 1',
  deleted: false,
  archived: false,
  air_weekday: 3,
  needs_review: false,
  needs_review_reason: null,
};

export const mockBangumiRule: BangumiRule = {
  ...mockBangumiAPI,
  filter: ['720'],
  rss_link: ['https://mikanani.me/RSS/test'],
};

export const mockBangumiList: BangumiAPI[] = [
  mockBangumiAPI,
  {
    ...mockBangumiAPI,
    id: 2,
    official_title: 'Another Anime',
    title_raw: '[TestGroup] Another Anime',
    deleted: false,
    archived: true,
  },
  {
    ...mockBangumiAPI,
    id: 3,
    official_title: 'Disabled Anime',
    title_raw: '[TestGroup] Disabled Anime',
    deleted: true,
    archived: false,
  },
];

// ============================================================================
// RSS Mocks
// ============================================================================

export const mockRSSItem: RSS = {
  id: 1,
  name: 'Test RSS Feed',
  url: 'https://mikanani.me/RSS/MyBangumi?token=test',
  aggregate: true,
  parser: 'mikan',
  enabled: true,
  connection_status: null,
  last_checked_at: null,
  last_error: null,
};

export const mockRSSList: RSS[] = [
  mockRSSItem,
  {
    ...mockRSSItem,
    id: 2,
    name: 'Another RSS Feed',
    enabled: false,
  },
];

// ============================================================================
// Config Mocks
// ============================================================================

export const mockConfig = {
  program: {
    rss_time: 900,
    rename_time: 60,
    webui_port: 7892,
  },
  downloader: {
    type: 'qbittorrent',
    host: '172.17.0.1:8080',
    username: 'admin',
    password: 'adminadmin',
    path: '/downloads/Bangumi',
    ssl: false,
  },
  rss_parser: {
    enable: true,
    filter: ['720', '\\d+-\\d'],
    language: 'zh',
  },
  bangumi_manage: {
    enable: true,
    eps_complete: false,
    rename_method: 'pn',
    group_tag: false,
    remove_bad_torrent: false,
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
  experimental_openai: {
    enable: false,
    api_key: '',
    api_base: 'https://api.openai.com/v1',
    api_type: 'openai',
    api_version: '2023-05-15',
    model: 'gpt-3.5-turbo',
    deployment_id: '',
  },
};

// ============================================================================
// Program Status Mocks
// ============================================================================

export const mockProgramStatus = {
  status: true,
  version: '3.2.0',
  first_run: false,
};

// ============================================================================
// Torrent Mocks
// ============================================================================

export const mockTorrents = [
  {
    hash: 'abc123',
    name: '[TestGroup] Test Anime - 01.mkv',
    state: 'downloading',
    progress: 0.5,
    size: 1073741824,
    dlspeed: 1048576,
  },
  {
    hash: 'def456',
    name: '[TestGroup] Test Anime - 02.mkv',
    state: 'completed',
    progress: 1.0,
    size: 1073741824,
    dlspeed: 0,
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Create a mock axios response
 */
export function createMockResponse<T>(data: T, status = 200) {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {},
  };
}

/**
 * Create a mock axios error
 */
export function createMockError(status: number, message: string) {
  const error = new Error(message) as any;
  error.response = {
    status,
    data: { msg_en: message, msg_zh: message },
  };
  error.isAxiosError = true;
  return error;
}
