import Axios from 'axios';
import type { ApiError } from '#/error';

export const axios = Axios.create();

axios.interceptors.request.use((config) => {
  const { auth } = useAuth();

  if (auth.value !== '' && config.headers) {
    config.headers.Authorization = auth.value;
  }

  return config;
});

axios.interceptors.response.use(
  (res) => {
    return res;
  },
  (err) => {
    const status = err.response.status as ApiError['status'];
    const detail = err.response.data.detail as ApiError['detail'];
    const error = {
      status,
      detail,
    };

    const message = useMessage();

    /** token 过期 */
    if (error.status === 401) {
      const { auth } = useAuth();
      auth.value = '';
    }

    if (error.status === 500) {
      const msg = error.detail ? error.detail : 'Request Error!';
      message.error(msg);
    }

    return Promise.reject(error);
  }
);
