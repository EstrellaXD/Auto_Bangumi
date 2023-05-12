import axios from 'axios';
import type { BangumiItem } from '#/bangumi';

/**
 * 添加番剧订阅
 * @param type 'new' 添加新番， ’old‘ 添加旧番
 * @param rss_link
 */
function addBangumi(type: string, rss_link: string) {
  if (type === 'new') {
    return axios.post('api/v1/subscribe', { rss_link });
  } else if (type === 'old') {
    return axios.post('api/v1/collection', { rss_link });
  } else {
    console.error('type错误, type应为 new 或 old');
    return false;
  }
}

/**
 *  获取订阅番剧数据
 */
const getABData = () => axios.get<BangumiItem[]>('api/v1/bangumi/getAll');

export { addBangumi, getABData };
