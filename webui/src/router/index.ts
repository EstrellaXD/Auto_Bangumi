import { createRouter, createWebHashHistory } from 'vue-router/auto';

const router = createRouter({
  history: createWebHashHistory(),
});

let setupChecked = false;
let needSetup = false;

// Called once the setup wizard finishes, so the next navigation isn't
// bounced back into /setup by the guard below.
export function markSetupComplete() {
  needSetup = false;
  setupChecked = true;
}

router.beforeEach(async (to) => {
  const { isLoggedIn } = useAuth();
  const { type, url } = storeToRefs(usePlayerStore());

  // Check setup status once per session. Skip while logged in: a session can
  // only exist after setup completed, so an authed navigation never needs the
  // gate — and awaiting this network call here is what wedged the post-login
  // redirect when the initial check had failed (setupChecked still false).
  if (!setupChecked && !isLoggedIn.value && to.path !== '/setup') {
    try {
      const status = await apiSetup.getStatus();
      needSetup = status.need_setup;
      setupChecked = true;
    } catch {
      // If check fails, retry on next navigation
    }
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
