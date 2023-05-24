import type { User } from '#/auth';

export const useAuth = createSharedComposable(() => {
  const auth = useLocalStorage('auth', '');

  const user = reactive<User>({
    username: '',
    password: '',
  });

  const isLogin = computed(() => auth.value !== '');

  const login = async () => {
    const res = await apiAuth.login(user.username, user.password);
    auth.value = `${res.token_type} ${res.access_token}`;
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
    auth,
    user,
    isLogin,

    login,
    logout,
    refresh,
    update,
  };
});
