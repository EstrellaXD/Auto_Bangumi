import axios from 'axios';

/**
 *  获取AB的日志
 */
async function getABLog() {
  const { data } = await axios.get('api/v1/log');
  return data;
}
/**
 * 重置 AB 的数据，程序会在下一轮检索中重新添加 RSS 订阅信息。
 */
const resetRule = () => axios.get('api/v1/resetRule');

export { getABLog, resetRule };
