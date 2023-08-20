import type { UniversalResponse } from "#/message";

export const apiLog = {
  async getLog() {
    const { data } = await axios.get<string>('api/v1/log');
    return data;
  },

  async clearLog() {
    const { data } = await axios.get<UniversalResponse>('api/v1/log/clear');
    return data;
  },
};
