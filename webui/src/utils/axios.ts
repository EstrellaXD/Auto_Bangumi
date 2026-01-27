import Axios from 'axios';
import type { AxiosError, AxiosResponse } from 'axios';
import type { ApiSuccess, StatusCode } from '#/api';

export const axios = Axios.create({
  withCredentials: true,
});

axios.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError<ApiSuccess>) => {
    const status = err.response?.status as StatusCode;
    const msg_en = err.response?.data?.msg_en ?? '';
    const msg_zh = err.response?.data?.msg_zh ?? '';

    const message = useMessage();
    const { returnUserLangText } = useMyI18n();

    const errorMsg = returnUserLangText({
      en: msg_en,
      'zh-CN': msg_zh,
    });

    const { isLoggedIn } = useAuth();

    // Handle network errors (no response from server)
    if (!err.response) {
      message.error(
        returnUserLangText({
          en: 'Network error. Please check your connection.',
          'zh-CN': '网络错误，请检查连接。',
        })
      );
      const error = {
        status: 0,
        msg_en: 'Network error',
        msg_zh: '网络错误',
      };
      return Promise.reject(error);
    }

    switch (status) {
      /** token 过期 - only logout on auth errors */
      case 401:
        isLoggedIn.value = false;
        if (errorMsg) message.error(errorMsg);
        break;
      /** 执行失败 */
      case 406:
        if (errorMsg) message.error(errorMsg);
        break;
      /** 服务器错误 - don't logout, just show error */
      case 500:
        message.error(
          errorMsg ||
            returnUserLangText({
              en: 'Server error. Please try again later.',
              'zh-CN': '服务器错误，请稍后重试。',
            })
        );
        break;
    }

    const error = {
      status,
      msg_en,
      msg_zh,
    };

    return Promise.reject(error);
  }
);
