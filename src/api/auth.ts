import type { LoginSuccess, Logout, Update } from '#/auth';

export const apiAuth = {
  async login(username: string, password: string) {
    const formData = new URLSearchParams({
      username,
      password,
    });

    const { data } = await axios.post<LoginSuccess>(
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
    const { data } = await axios.get<LoginSuccess>('api/v1/auth/refresh_token');
    return data;
  },

  async logout() {
    const { data } = await axios.get<Logout>('api/v1/auth/logout');
    return data.message === 'logout success';
  },

  async update(username: string, password: string) {
    const message = useMessage();
    if (password.length < 8) {
      message.error('密码至少8个字符!');
      return;
    } else {
      const { data } = await axios.post<Update>('api/v1/auth/update', {
        username,
        password,
      });

      return data.message === 'update success';
    }
  },
};
