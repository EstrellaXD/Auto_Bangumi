import { createRouter, createWebHashHistory } from 'vue-router/auto';

const router = createRouter({
  history: createWebHashHistory(),
});

let setupChecked = false;
let needSetup = false;

router.beforeEach(async (to) => {
  const { isLoggedIn } = useAuth();
  const { type, url } = storeToRefs(usePlayerStore());

  // Check setup status once per session
  if (!setupChecked && to.path !== '/setup') {
    try {
      const status = await apiSetup.getStatus();
      needSetup = status.need_setup;
    } catch {
      // If check fails, proceed normally
    }
    setupChecked = true;
  }

  // Redirect to setup if needed
  if (needSetup && to.path !== '/setup') {
    return { name: 'Setup' };
  }

  // Prevent going to setup after it's completed
  if (to.path === '/setup' && setupChecked && !needSetup) {
    return { name: 'Login' };
  }

  if (!isLoggedIn.value && to.path !== '/login' && to.path !== '/setup') {
    return { name: 'Login' };
  } else if (isLoggedIn.value && to.path === '/login') {
    return { name: 'Index' };
  }

  if (type.value === 'jump' && url.value !== '' && to.path === '/player') {
    open(url.value);
    return false;
  }
});

export { router };
