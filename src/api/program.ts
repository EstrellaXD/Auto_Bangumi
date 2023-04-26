import axios from 'axios';

/** 重启 */
export const appRestart = () => axios.get('api/v1/restart');

/** 启动 */
export const appStart = () => axios.get('api/v1/start');

/** 停止 */
export const appStop = () => axios.get('api/v1/stop');

/** 状态 */
export async function appStatus() {
  const { data } = await axios.get('api/v1/getStatus');
  return data;
}
