import axios from 'axios';

interface Success {
  status: 'ok';
}

export const apiProgram = {
  /**
   * 重启
   */
  async restart() {
    const { data } = await axios.get<Success>('api/v1/restart');
    return data.status === 'ok';
  },

  /**
   * 启动
   */
  async start() {
    const { data } = await axios.get<Success>('api/v1/start');
    return data.status === 'ok';
  },

  /**
   * 停止
   */
  async stop() {
    const { data } = await axios.get<Success>('api/v1/stop');
    return data.status === 'ok';
  },

  /**
   * 状态
   */
  async status() {
    const { data } = await axios.get<{ status: 'running' | 'stop' }>(
      'api/v1/status'
    );
    return data.status === 'running';
  },

  /**
   * 终止
   */
  async shutdown() {
    const { data } = await axios.get<Success>('api/v1/shutdown');
    return data.status === 'ok';
  },
};
