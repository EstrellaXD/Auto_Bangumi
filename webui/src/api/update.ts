import type { UpdateApplyResult, UpdateInfo } from '#/update';

export const apiUpdate = {
  /**
   * 检查更新：查询 GitHub Release，返回最新版本、更新提示与本地覆盖层状态。
   * @param channel - 更新渠道（stable/beta），省略则用后端配置的默认渠道
   */
  async check(channel?: string) {
    const { data } = await axios.get<UpdateInfo>('api/v1/update/check', {
      params: channel ? { channel } : undefined,
    });
    return data;
  },

  /**
   * 应用更新：下载 bundle → 校验 → 落地覆盖层；成功后后端会重启进程以生效。
   * @param channel - 更新渠道（stable/beta）
   */
  async apply(channel?: string) {
    const { data } = await axios.post<UpdateApplyResult>(
      'api/v1/update/apply',
      null,
      { params: channel ? { channel } : undefined }
    );
    return data;
  },

  /**
   * 回滚：换回上一个覆盖层版本（无备份则回退到镜像版本）；成功后重启生效。
   */
  async rollback() {
    const { data } = await axios.post<UpdateApplyResult>(
      'api/v1/update/rollback'
    );
    return data;
  },
};
