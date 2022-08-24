import axios from "axios";


/**
 * 添加番剧订阅
 * @param type 'new' 添加新番， ’old‘ 添加旧番
 * @param rss_link 
 */
const addBangumi = (type: string, rss_link: string) => {
  if(type === 'new') {
    return axios.post('api/v1/subscribe', { rss_link });
  } else if(type === 'old') {
    return axios.post('api/v1/collection', { rss_link });
  } else {
    console.error('type错误, type应为 new 或 old');
    return false;
  }
}

/**
 *  获取AB存储的数据 
 */
const getABData = () => axios.get('api/v1/data');

/**
 * 删除番剧规则
 * @param {string} name 番名 (title_raw)
 */
const removeRule = (name: string) => axios.get(`api/v1/removeRule/${name}`);

export {
  addBangumi,
  getABData,
  removeRule
}