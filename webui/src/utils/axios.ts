import Axios from 'axios';
import type {ApiError} from "#/api";

export const axios = Axios.create();

// axios.interceptors.request.use((config) => {
//   const { auth } = useAuth();
//
//   // if (auth.value !== '' && config.headers) {
//   //   config.headers.Authorization = auth.value;
//   // }
//
//   return config;
// });

// axios.defaults.baseURL = '/api/v1';
axios.defaults.withCredentials = true;

axios.interceptors.response.use(
    (res) => {
        return res;
    },
    (err) => {
        const status = err.response.status as ApiError['status'];
        const msg_en = (err.response.data.msg_en ?? '') as ApiError['msg_en'];
        const msg_zh = (err.response.data.msg_zh ?? '') as ApiError['msg_zh'];

        const error = {
            status,
            msg_en,
            msg_zh,
        };

        const message = useMessage();

        /** token 过期 */
        if (error.status === 401) {
            const {auth} = useAuth();
            auth.value = '';
        }

        /** 执行失败 */
        if (error.status === 406) {
            message.error(error.msg_zh);
        }

        if (error.status === 500) {
            const msg = (err.response.data.msg_en ?? '') as ApiError['msg_en']
            message.error(msg);
        }

        return Promise.reject(error);
    }
);
