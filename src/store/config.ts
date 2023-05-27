import type { Config } from '#/config';

export const useConfigStore = defineStore('config', () => {
  const message = useMessage();
  const config = ref<Config>({
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
  });

  const getConfig = async () => {
    const res = await apiConfig.getConfig();
    config.value = res;
  };

  const setConfig = async () => {
    const status = await apiConfig.updateConfig(config.value);
    if (status) {
      message.success('apply success!');
    } else {
      message.error('apply fail!');
    }
  };

  const getSettingGroup = <Tkey extends keyof Config>(key: Tkey) => {
    return computed<Config[Tkey]>(() => config.value[key]);
  };

  return {
    config,
    getConfig,
    setConfig,
    getSettingGroup,
  };
});
