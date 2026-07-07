/**
 * Auto passkey prompt: the login page auto-triggers passkey auth for users
 * who have used a passkey in this browser before. usePasskey must remember
 * successful passkey use (hasKnownPasskey), and silent mode must distinguish
 * a WebAuthn ceremony abort (DOMException: user cancel / no credential /
 * gesture requirement — disarm the auto prompt, no toast) from API errors
 * (axios interceptor already toasts; keep the flag) so a stale flag
 * self-heals instead of dooming every login-page visit to a dead prompt.
 * An explicit logout suppresses the next auto prompt via sessionStorage so
 * a reflexive Touch ID confirmation can't immediately log the user back in.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { withSetup } from './test-utils';
import { apiAuth } from '@/api/auth';
import { loginWithPasskey as webauthnLogin } from '@/services/webauthn';
import { useMessage } from '@/hooks/useMessage';
import { useAuth } from '@/hooks/useAuth';
import { usePasskey } from '@/hooks/usePasskey';

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

vi.mock('@/hooks/useMessage', () => {
  // 单例：让测试能拿到与被测代码相同的 error mock
  const msg = { success: vi.fn(), error: vi.fn(), warning: vi.fn() };
  return { useMessage: () => msg };
});

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (k: string) => k,
    returnUserLangText: (x: { en: string }) => x.en,
  }),
}));

const passkeyLogin = webauthnLogin as unknown as ReturnType<typeof vi.fn>;
const apiLogout = apiAuth.logout as ReturnType<typeof vi.fn>;
const messageError = useMessage().error as ReturnType<typeof vi.fn>;

function ceremonyAbort(): DOMException {
  return new DOMException(
    'The operation either timed out or was not allowed',
    'NotAllowedError'
  );
}

describe('passkey auto login memory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    // usePasskey is a shared composable: reset the flag between tests
    withSetup(() => usePasskey()).hasKnownPasskey.value = false;
  });

  it('should remember passkey availability after a successful passkey login', async () => {
    passkeyLogin.mockResolvedValue(undefined);
    const { loginWithPasskey, hasKnownPasskey } = withSetup(() =>
      usePasskey()
    );

    expect(hasKnownPasskey.value).toBe(false);
    await loginWithPasskey('admin');

    expect(hasKnownPasskey.value).toBe(true);
  });

  it('should not remember passkey when login fails', async () => {
    passkeyLogin.mockRejectedValue({ status: 401 });
    const { loginWithPasskey, hasKnownPasskey } = withSetup(() =>
      usePasskey()
    );

    await loginWithPasskey('admin');

    expect(hasKnownPasskey.value).toBe(false);
  });

  it('should disarm the auto prompt when a silent ceremony is cancelled', async () => {
    passkeyLogin.mockRejectedValue(ceremonyAbort());
    const { loginWithPasskey, hasKnownPasskey } = withSetup(() =>
      usePasskey()
    );
    hasKnownPasskey.value = true;

    const ok = await loginWithPasskey(undefined, { silent: true });

    expect(ok).toBe(false);
    expect(hasKnownPasskey.value).toBe(false);
    expect(messageError).not.toHaveBeenCalled();
  });

  it('should keep the flag when a silent attempt fails with an API error', async () => {
    // 服务器抖动不代表凭证失效；axios 拦截器已负责提示
    passkeyLogin.mockRejectedValue({ status: 500 });
    const { loginWithPasskey, hasKnownPasskey } = withSetup(() =>
      usePasskey()
    );
    hasKnownPasskey.value = true;

    const ok = await loginWithPasskey(undefined, { silent: true });

    expect(ok).toBe(false);
    expect(hasKnownPasskey.value).toBe(true);
    expect(messageError).not.toHaveBeenCalled();
  });

  it('should show the error toast when a manual login is cancelled', async () => {
    passkeyLogin.mockRejectedValue(ceremonyAbort());
    const { loginWithPasskey } = withSetup(() => usePasskey());

    const ok = await loginWithPasskey(undefined);

    expect(ok).toBe(false);
    expect(messageError).toHaveBeenCalled();
  });

  it('should suppress the next auto prompt after an explicit logout', async () => {
    apiLogout.mockResolvedValue({});
    const { logout } = withSetup(() => useAuth());

    await logout();

    expect(sessionStorage.getItem('suppressPasskeyAutoPrompt')).toBe('1');
  });
});
