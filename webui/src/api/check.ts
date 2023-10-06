export const apiCheck = {
  /**
   * 检测下载器
   */
  async downloader() {
    const { data } = await axios.get<Boolean>('api/v1/check/downloader');
    return data;
  },
};
