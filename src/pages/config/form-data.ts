import type {
  Config,
  DownloaderType,
  NotificationType,
  ProxyType,
  RenameMethod,
  RssParserLang,
  RssParserType,
} from '#/config';

export const form = reactive<Config>({
  data_version: 4,
  program: {
    sleep_time: 0,
    rename_times: 0,
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
    enable_tmdb: false,
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
    type: 'telegram',
    token: '',
    chat_id: '',
  },
});

export const downloaderType: DownloaderType = ['qbittorrent'];
export const rssParserType: RssParserType = ['mikan'];
export const rssParserLang: RssParserLang = ['zh', 'en', 'jp'];
export const renameMethod: RenameMethod = ['normal', 'pn', 'advance', 'none'];
export const proxyType: ProxyType = ['http', 'https', 'socks5'];
export const notificationType: NotificationType = ['telegram', 'server-chan', 'bark'];
export const tfOptions = [
  { label: '是', value: true },
  { label: '否', value: false },
];
