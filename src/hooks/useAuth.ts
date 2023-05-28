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

  const clearUser = () => {
    user.username = '';
    user.password = '';
  };

  const check = () => {
    if (user.username === '') {
      message.warning('Please Enter Username!');
      return false;
    }

    if (user.password === '') {
      message.warning('Please Enter Password!');
      return false;
    }

    return true;
  };

  const login = async () => {
    try {
      if (check()) {
        const res = await apiAuth.login(user.username, user.password);
        auth.value = `${res.token_type} ${res.access_token}`;
        clearUser();
        message.success('Login Success!');
      }
    } catch (err) {
      const error = err as ApiError;
      message.error(error.detail);
    }
  };

  const logout = async () => {
    const res = await apiAuth.logout();
    if (res) {
      clearUser();
      auth.value = '';
      message.success('Logout Success!');
    } else {
      message.error('Logout Failed!');
    }
  };

  const refresh = () => {
    apiAuth.refresh();
  };

  const update = async () => {
    try {
      const res = await apiAuth.update(user.username, user.password);

      if (res?.message === 'update success') {
        auth.value = `${res.token_type} ${res.access_token}`;
        message.success('Update Success!');
        clearUser();
      } else {
        message.error('Update Failed!');
        user.password = '';
      }
    } catch (error) {
      message.error('Update Failed!');
    }
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
