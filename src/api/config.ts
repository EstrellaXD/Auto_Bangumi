import axios from 'axios';

export const setConfig = () => axios.post('/api/v1/updateConfig');

export const getConfig = () => axios.post('/api/v1/getConfig');
