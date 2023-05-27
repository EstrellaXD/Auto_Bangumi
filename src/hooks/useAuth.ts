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
      message.error('Logout Fail!');
    }
  };

  const refresh = () => {
    apiAuth.refresh();
  };

  const update = async () => {
    const res = await apiAuth.update(user.username, user.password);
    if (res) {
      message.success('Update Success!');
      clearUser();
    } else if (res === false) {
      message.error('Update Fail!');
    } else {
      user.password = '';
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
