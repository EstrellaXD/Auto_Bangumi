import axios from 'axios';

/** 重启 */
export const appRestart = () => axios.get('/api/v1/restart');
