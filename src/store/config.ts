import { defineStore } from 'pinia';

export interface Config {
  data_version: 4;
  program: {
    sleep_time: number;
    rename_times: number;
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
    type: string;
    token: string;
    custom_url: string;
    enable_tmdb: boolean;
    filter: Array<string>;
    language: 'zh' | 'en' | 'jp';
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
    type: 'http' | 'https';
    host: string;
    port: number;
    username: string;
    password: string;
  };
  notification: {
    enable: boolean;
    type: 'telegram' | 'server-chan';
    token: string;
    chat_id: string;
  };
}

export const configStore = defineStore('config', () => {
  const config = ref(null);
});
