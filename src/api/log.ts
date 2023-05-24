export const apiLog = {
  async getLog() {
    const { data } = await axios.get('api/v1/log');
    return data;
  },
};
