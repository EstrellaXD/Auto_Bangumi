import type { ApiResponse } from "#/api";

export const apiLog = {
  async getLog() {
    const { data } = await axios.get<string>('api/v1/log');
    return data;
  },

  async clearLog() {
    const { data } = await axios.get<ApiResponse>('api/v1/log/clear');
    return data;
  },
};
