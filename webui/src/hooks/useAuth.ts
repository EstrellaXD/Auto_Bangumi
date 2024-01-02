import type { User } from '#/auth';
import type { ApiError } from '#/api';

export const useAuth = createSharedComposable(() => {
  const isLoggedin = useLocalStorage('isLoggedin', false);
  const message = useMessage();

  const user = reactive<User>({
    username: '',
    password: '',
  });


  function clearUser() {
    user.username = '';
    user.password = '';
  }

  function check() {
    if (user.username === '') {
      message.warning('Please Enter Username!');
      return false;
    }

    if (user.password === '') {
      message.warning('Please Enter Password!');
      return false;
    }

    return true;
  }

  function login() {
    const { execute, onResult, onError } = useApi(apiAuth.login, {
      message: {
        success: 'Login Success!',
      },
    });

    onResult((res) => {
      isLoggedin.value = true;
      clearUser();
    });

    onError((err) => {
      const error = err as ApiError;

      if (error.status === 404) {
        message.error('请更新AutoBangumi!');
      } else if (error.status === 401) {
        message.error(err.msg_zh);
      }
    });

    if (check()) {
      execute(user.username, user.password);
    }
  }

  const { execute: logout, onResult: onLogoutResult } = useApi(apiAuth.logout, {
    failRule: (res) => !res,
    message: {
      success: 'Logout Success!',
      fail: 'Logout Failed!',
    },
  });

  onLogoutResult(() => {
    clearUser();
    isLoggedin.value = false;
  });

  const { execute: refresh, onResult: onRefreshResult } = useApi(
    apiAuth.refresh
  );

  onRefreshResult((res) => {
    isLoggedin.value = true;
  });

  function update() {
    const { execute, onResult } = useApi(apiAuth.update, {
      failRule: (res) => res.message !== 'update success',
      message: {
        success: 'Update Success!',
        fail: 'Update Failed!',
      },
    });

    onResult((res) => {
      if (res.message === 'update success') {
        clearUser();
      } else {
        user.password = '';
      }
    });

    if (check()) {
      if (user.password.length < 8) {
        message.error('Password must be at least 8 characters long!');
      } else {
        execute(user.username, user.password);
      }
    }
  }

  return {
    isLoggedin,
    user,

    login,
    logout,
    refresh,
    update,
  };
});
