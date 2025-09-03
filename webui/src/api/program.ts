import type { ApiSuccess } from '#/api';

export const apiProgram = {
  /**
   * 重启
   */
  async restart() {
    const { data } = await axios.get<ApiSuccess>('api/v1/restart');
    return data;
  },

  /**
   * 启动
   */
  async start() {
    const { data } = await axios.get<ApiSuccess>('api/v1/start');
    return data;
  },

  /**
   * 停止
   */
  async stop() {
    const { data } = await axios.get<ApiSuccess>('api/v1/stop');
    return data;
  },

  /**
   * 状态
   */
  async status() {
    const { data } = await axios.get<{ status: boolean; version: string }>(
      'api/v1/status'
    );

    return data!;
  },

  /**
   * 终止
   */
  async shutdown() {
    const { data } = await axios.get<ApiSuccess>('api/v1/shutdown');
    return data;
  },

  /**
   * 检查更新
   */
  async checkUpdate(includePrerelease = false) {
    const { data } = await axios.get<{
      current_version: string;
      latest_version: string;
      has_update: boolean;
      release_info: {
        name: string;
        html_url: string;
        published_at: string;
        prerelease: boolean;
        download_url: string;
      };
    }>(`api/v1/check/update?include_prerelease=${includePrerelease}`);
    return data;
  },

  /**
   * 执行更新
   */
  async update(downloadUrl: string) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/program/update',
      null,
      {
        params: { download_url: downloadUrl }
      }
    );
    return data;
  },
};
