export const apiCheck = {
  /**
   * 检测下载器
   */
  async downloader() {
    const { data } = await axios.get('api/v1/check/downloader');
    return data;
  },

  /**
   * 检测 RSS
   */
  async rss() {
    const { data } = await axios.get('api/v1/check/rss');
    return data;
  },

  /**
   * 检测所有
   */
  async all() {
    const { data } = await axios.get('api/v1/check');
    return data;
  },
};
