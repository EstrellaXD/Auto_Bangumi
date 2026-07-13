import type { SessionSuccess, Update } from '#/auth';
import type { ApiSuccess } from '#/api';

export const apiAuth = {
  async login(username: string, password: string) {
    const formData = new URLSearchParams({
      username,
      password,
    });

    const { data } = await axios.post<SessionSuccess>(
      'api/v1/auth/login',
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );

    return data;
  },

  async refresh() {
    // silent: a startup refresh of an expired session must not flash a scary
    // error toast — the 401 handler still logs out and routes to /login.
    const { data } = await axios.post<SessionSuccess>(
      'api/v1/auth/refresh_token',
      undefined,
      { silent: true }
    );
    return data;
  },

  async logout() {
    const { data } = await axios.post<ApiSuccess>('api/v1/auth/logout');
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
