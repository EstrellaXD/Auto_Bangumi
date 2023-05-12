import axios from 'axios';
import type { Config } from '#/config';

export async function setConfig(newConfig: Config) {
  const { data } = await axios.post<{
    message: 'Success' | 'Failed to update config';
  }>('api/v1/updateConfig', newConfig);

  return data.message === 'Success';
}

export async function getConfig() {
  const { data } = await axios.get<Config>('api/v1/getConfig');
  return data;
}
