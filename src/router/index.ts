import { createRouter, createWebHashHistory } from 'vue-router/auto';

const router = createRouter({
  history: createWebHashHistory(),
});

router.beforeEach((to) => {
  const { isLogin } = useAuth();
  if (!isLogin.value && to.path !== '/login') {
    return { name: 'Login' };
  }
});

export { router };
