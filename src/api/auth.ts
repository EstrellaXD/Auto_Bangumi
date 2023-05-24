import axios from 'axios';
import type { Auth, Logout, Update } from '#/auth';

export const apiAuth = {
  async login(username: string, password: string) {
    const { data } = await axios.post<Auth>(
      'api/v1/auth/login',
      {
        username,
        password,
      },
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );

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

  async update(username: string, password: string) {
    const { data } = await axios.post<Update>('api/v1/auth/update', {
      username,
      password,
    });
    return data;
  },
};
