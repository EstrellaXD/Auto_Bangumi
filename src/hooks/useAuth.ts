import type { User } from '#/auth';
import type { ApiError } from '#/error';

export const useAuth = createSharedComposable(() => {
  const auth = useLocalStorage('auth', '');
  const message = useMessage();

  const user = reactive<User>({
    username: '',
    password: '',
  });

  const isLogin = computed(() => auth.value !== '');

  const login = async () => {
    try {
      const res = await apiAuth.login(user.username, user.password);
      auth.value = `${res.token_type} ${res.access_token}`;
      user.username = '';
      user.password = '';
    } catch (err) {
      const error = err as ApiError;
      message.error(error.detail);
    }
  };

  const logout = async () => {
    apiAuth.logout();
  };

  const refresh = () => {
    apiAuth.refresh();
  };

  const update = async () => {
    const res = await apiAuth.update(user.username, user.password);
    console.log(res);
  };

  return {
    auth,
    user,
    isLogin,

    login,
    logout,
    refresh,
    update,
  };
});
