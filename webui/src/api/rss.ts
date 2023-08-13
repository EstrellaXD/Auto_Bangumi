import type { RSS } from '#/rss';

export const apiRSS = {
  async get() {
    const { data } = await axios.get<RSS[]>('api/v1/rss');
    return data!;
  },

  async add() {
    const { data } = await axios.post<RSS>('api/v1/rss/add', {});
    return data!;
  },
};
