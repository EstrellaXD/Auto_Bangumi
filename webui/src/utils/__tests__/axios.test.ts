/**
 * The response-error interceptor is the single place that reacts to auth
 * failures. A 401 must both drop the logged-in flag AND route back to
 * /login — otherwise an expired session leaves the user stranded on an
 * unauthorized page showing stale data (the logout-side analog of the
 * passkey "logged in but never navigated" bug).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { onResponseError } from '@/utils/axios';
import { router } from '@/router';
import { useAuth } from '@/hooks/useAuth';

const isLoggedIn = ref(true);

vi.mock('@/router', () => ({
  router: {
    replace: vi.fn(),
    currentRoute: { value: { path: '/bangumi', name: 'Bangumi' } },
  },
  markSetupComplete: vi.fn(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ isLoggedIn }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (k: string) => k,
    returnUserLangText: (x: { en: string }) => x.en,
  }),
}));

vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ error: vi.fn(), success: vi.fn(), warning: vi.fn() }),
}));

const replace = router.replace as ReturnType<typeof vi.fn>;

function errorWith(status: number, opts: { silent?: boolean } = {}) {
  return {
    response: { status, data: {} },
    config: { silent: opts.silent ?? false },
  } as never;
}

describe('axios response error interceptor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    isLoggedIn.value = true;
    (router.currentRoute as { value: { path: string; name: string } }).value = {
      path: '/bangumi',
      name: 'Bangumi',
    };
    useAuth(); // ensure shared state wired
  });

  it('should drop auth and redirect to login on 401 from an app page', async () => {
    await expect(onResponseError(errorWith(401))).rejects.toBeTruthy();
    expect(isLoggedIn.value).toBe(false);
    expect(replace).toHaveBeenCalledWith({ name: 'Login' });
  });

  it('should not redirect when the 401 happens on the login page', async () => {
    (router.currentRoute as { value: { path: string; name: string } }).value = {
      path: '/login',
      name: 'Login',
    };
    await expect(onResponseError(errorWith(401))).rejects.toBeTruthy();
    expect(isLoggedIn.value).toBe(false);
    expect(replace).not.toHaveBeenCalled();
  });

  it('should redirect on a silent 401 (background poll) too', async () => {
    await expect(
      onResponseError(errorWith(401, { silent: true }))
    ).rejects.toBeTruthy();
    expect(isLoggedIn.value).toBe(false);
    expect(replace).toHaveBeenCalledWith({ name: 'Login' });
  });

  it('should not redirect or logout on a non-auth error (500)', async () => {
    await expect(onResponseError(errorWith(500))).rejects.toBeTruthy();
    expect(isLoggedIn.value).toBe(true);
    expect(replace).not.toHaveBeenCalled();
  });
});
