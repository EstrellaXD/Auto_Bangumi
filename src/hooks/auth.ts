import type { User } from '#/auth';

export const useAuth = createSharedComposable(() => {
  const token = useLocalStorage('token', '');

  const user = reactive<User>({
    username: '',
    password: '',
  });

  const isLogin = computed(() => token.value !== '');

  const login = async () => {
    const res = await apiAuth.login(user.username, user.password);
    console.log(res);
  };

  const logout = async () => {
    apiAuth.logout();
  };

  const refresh = async () => {
    const res = await apiAuth.refresh();
  };

  const update = async () => {
    const res = await apiAuth.update(user.username, user.password);
    console.log(res);
  };

  return {
    token,
    user,
    isLogin,

    login,
    logout,
    refresh,
    update,
  };
});
