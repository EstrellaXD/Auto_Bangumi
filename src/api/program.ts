import axios from 'axios';

/** 重启 */
export async function appRestart() {
  const { data } = await axios.get<{ status: 'ok' }>('api/v1/restart');
  return data.status === 'ok';
}

/** 启动 */
export const appStart = () => axios.get('api/v1/start');

/** 停止 */
export const appStop = () => axios.get('api/v1/stop');

/** 状态 */
export async function appStatus() {
  const { data } = await axios.get<{ status: 'stop' | 'running' }>(
    'api/v1/status'
  );
  return data.status !== 'stop';
}
