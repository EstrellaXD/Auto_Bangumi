/**
 * Reproduces the "login sometimes gets stuck, no redirect" report: after a
 * successful login the app must navigate to Index. Passkey login regressed
 * because its success path set isLoggedIn but never navigated, and
 * useAuth.login didn't return its promise so callers couldn't await it.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { withSetup } from './test-utils';
import { router } from '@/router';
import { apiAuth } from '@/api/auth';
import { loginWithPasskey as webauthnLogin } from '@/services/webauthn';
import { useAuth } from '@/hooks/useAuth';
import { usePasskey } from '@/hooks/usePasskey';

// vi.mock is hoisted above the imports above regardless of textual order.
vi.mock('@/router', () => ({
  router: { replace: vi.fn(), push: vi.fn() },
  markSetupComplete: vi.fn(),
}));

vi.mock('@/api/auth', () => ({
  apiAuth: {
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    update: vi.fn(),
  },
}));

vi.mock('@/services/webauthn', () => ({
  isWebAuthnSupported: () => true,
  registerPasskey: vi.fn(),
  loginWithPasskey: vi.fn(),
}));

vi.mock('@/api/passkey', () => ({
  apiPasskey: { list: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (k: string) => k,
    returnUserLangText: (x: { en: string }) => x.en,
  }),
}));

const replace = router.replace as ReturnType<typeof vi.fn>;
const apiLogin = apiAuth.login as ReturnType<typeof vi.fn>;
const apiUpdate = apiAuth.update as ReturnType<typeof vi.fn>;
const passkeyLogin = webauthnLogin as unknown as ReturnType<typeof vi.fn>;

describe('login redirect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('should navigate to Index after a successful password login', async () => {
    apiLogin.mockResolvedValue({ authenticated: true });
    const { user, login } = withSetup(() => useAuth());
    user.username = 'admin';
    user.password = 'validpassword123';

    // login() must return a promise so the caller (login.vue) can await it
    await login();

    expect(replace).toHaveBeenCalledWith({ name: 'Index' });
  });

  it('should accept the non-secret session response after updating credentials', async () => {
    apiUpdate.mockResolvedValue({ authenticated: true });
    const { user, update } = withSetup(() => useAuth());
    user.username = 'newadmin';
    user.password = 'newpassword123';

    await update();

    expect(apiUpdate).toHaveBeenCalledWith('newadmin', 'newpassword123');
    expect(user.username).toBe('');
    expect(user.password).toBe('');
  });

  it('should navigate to Index after a successful passkey login', async () => {
    passkeyLogin.mockResolvedValue(undefined);
    const { loginWithPasskey } = withSetup(() => usePasskey());

    const ok = await loginWithPasskey('admin');

    expect(ok).toBe(true);
    expect(replace).toHaveBeenCalledWith({ name: 'Index' });
  });

  it('should not navigate when passkey login fails', async () => {
    passkeyLogin.mockRejectedValue({ status: 401 });
    const { loginWithPasskey } = withSetup(() => usePasskey());

    const ok = await loginWithPasskey('admin');

    expect(ok).toBe(false);
    expect(replace).not.toHaveBeenCalled();
  });
});
