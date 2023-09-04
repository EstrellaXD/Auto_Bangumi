import type { RSS } from '#/rss';
import type { Torrent } from '#/torrent';
import type { ApiSuccess } from '#/api';

export const apiRSS = {
  async get() {
    const { data } = await axios.get<RSS[]>('api/v1/rss');
    return data!;
  },

  async add(rss: RSS) {
    const { data } = await axios.post<ApiSuccess>('api/v1/rss/add', rss);
    return data;
  },

  async delete(rss_id: number) {
    const { data } = await axios.delete<ApiSuccess>(`api/v1/rss/delete/${rss_id}`);
    return data!;
  },

  async deleteMany(rss_list: number[]) {
    const { data } = await axios.post<ApiSuccess>(`api/v1/rss/delete/many`, rss_list);
    return data!;
  },

  async disable(rss_id: number) {
    const { data } = await axios.patch<ApiSuccess>(`api/v1/rss/disable/${rss_id}`);
    return data!;
  },

  async disableMany(rss_list: number[]) {
    const { data } = await axios.post<ApiSuccess>(`api/v1/rss/disable/many`, rss_list);
    return data!;
  },

  async update(rss_id: number, rss: RSS) {
    const { data } = await axios.patch<ApiSuccess>(`api/v1/rss/update/${rss_id}`, rss);
    return data!;
  },

  async refreshAll() {
    const { data } = await axios.get<ApiSuccess>('api/v1/rss/refresh/all');
    return data!;
  },

  async refresh(rss_id: number) {
    const { data } = await axios.get<ApiSuccess>(`api/v1/rss/refresh/${rss_id}`);
    return data!;
  },

  async getTorrent(rss_id: number) {
    const { data } = await axios.get<Torrent[]>(`api/v1/rss/torrent/${rss_id}`);
    return data!;
  },
};
