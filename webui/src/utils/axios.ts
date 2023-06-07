import Axios from 'axios';
import type { ApiError } from '#/api';

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
    const detail = (err.response.data.detail ?? '') as ApiError['detail'];
    const msg = (err.response.data.msg ?? '') as ApiError['msg'];

    const error = {
      status,
      detail,
      msg,
    };

    const message = useMessage();

    /** token 过期 */
    if (error.status === 401) {
      const { auth } = useAuth();
      auth.value = '';
    }

    /** 执行失败 */
    if (error.status === 406) {
      message.error(error.msg);
    }

    if (error.status === 500) {
      const msg = error.detail ? error.detail : 'Request Error!';
      message.error(msg);
    }

    return Promise.reject(error);
  }
);
