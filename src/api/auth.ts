import axios from 'axios';
import type { Auth, Logout, Update } from '#/auth';

export const apiAuth = {
  async login() {
    const { data } = await axios.post<Auth>('api/v1/auth/login');
    return data;
  },

  async refresh() {
    const { data } = await axios.get<Auth>('api/v1/auth/refresh_token');
    return data;
  },

  async logout() {
    const { data } = await axios.get<Logout>('api/v1/auth/logout');
    return data;
  },

  async update() {
    const { data } = await axios.post<Update>('api/v1/auth/update');
    return data;
  },
};
