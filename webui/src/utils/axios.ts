import Axios from 'axios';
import type { AxiosError, AxiosResponse } from 'axios';
import type { ApiSuccess, StatusCode } from '#/api';

export const axios = Axios.create({
  withCredentials: true,
});

// Throttle repeated identical error toasts (e.g. background polling during a
// backend restart would otherwise fire the same "Network error" toast once
// per failed request and produce a toast storm).
const recentToastAt = new Map<string, number>();
const TOAST_THROTTLE_MS = 4000;

function showErrorThrottled(msg: string) {
  const now = Date.now();
  const last = recentToastAt.get(msg) ?? 0;
  if (now - last < TOAST_THROTTLE_MS) return;
  recentToastAt.set(msg, now);
  useMessage().error(msg);
}

axios.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError<ApiSuccess>) => {
    const status = err.response?.status as StatusCode;
    const msg_en = err.response?.data?.msg_en ?? '';
    const msg_zh = err.response?.data?.msg_zh ?? '';

    const { returnUserLangText } = useMyI18n();

    const errorMsg = returnUserLangText({
      en: msg_en,
      'zh-CN': msg_zh,
    });

    const { isLoggedIn } = useAuth();

    // Handle network errors (no response from server)
    if (!err.response) {
      showErrorThrottled(
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
        if (errorMsg) showErrorThrottled(errorMsg);
        break;
      /** 执行失败 */
      case 406:
        if (errorMsg) showErrorThrottled(errorMsg);
        break;
      /** 服务器错误 - don't logout, just show error */
      case 500:
        showErrorThrottled(
          errorMsg ||
            returnUserLangText({
              en: 'Server error. Please try again later.',
              'zh-CN': '服务器错误，请稍后重试。',
            })
        );
        break;
      /** Anything else (400/404/422/...) - still surface it instead of
       * failing silently */
      default:
        showErrorThrottled(
          errorMsg ||
            returnUserLangText({
              en: 'Request failed. Please try again.',
              'zh-CN': '请求失败，请重试。',
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
