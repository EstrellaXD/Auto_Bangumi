import { createRouter, createWebHashHistory } from 'vue-router/auto';

const router = createRouter({
  history: createWebHashHistory(),
});

router.beforeEach((to) => {
  const { isLoggedin } = useAuth();
  const { type, url } = storeToRefs(usePlayerStore());

  if (!isLoggedin.value && to.path !== '/login') {
    return { name: 'Login' };
  }

  if (isLoggedin.value && to.path === '/login') {
    return { name: 'Index' };
  }

  if (type.value === 'jump' && url.value !== '' && to.path === '/player') {
    open(url.value);
    return false;
  }

  watch(isLoggedin, (val) => {
    if (to.path === '/login' && val) {
      router.replace({ name: 'Index' });
    }
    if (to.path !== '/login' && !val) {
      router.replace({ name: 'Login' });
    }
  });
});

export { router };
