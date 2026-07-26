import { readFileSync } from 'node:fs';
import { reactive, ref } from 'vue';
import type { Component } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import AbButton from '@/components/basic/ab-button.vue';
import { useAuth } from '@/hooks/useAuth';
import { usePasskey } from '@/hooks/usePasskey';

vi.mock('@/hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('@/hooks/usePasskey', () => ({ usePasskey: vi.fn() }));

const user = reactive({ username: '', password: '' });
const isSupported = ref(true);
const hasKnownPasskey = ref(false);
const login = vi.fn<[], Promise<void>>();
const loginWithPasskey = vi.fn<
  [string | undefined, { silent?: boolean }?],
  Promise<boolean>
>();

let LoginPage: Component;

function mountLogin() {
  return mount(LoginPage, {
    global: {
      components: { AbButton },
      mocks: {
        $t: (key: string) => key,
      },
    },
  });
}

function readLoginSource(): string {
  return readFileSync(new URL('../login.vue', import.meta.url), 'utf8');
}

function phoneStyles(): string {
  const source = readLoginSource();
  const start = source.indexOf('@media screen and (max-width: 639px)');

  return start === -1 ? '' : source.slice(start);
}

function scssBlock(source: string, selector: string): string {
  const selectorStart = source.indexOf(selector);
  const blockStart = source.indexOf('{', selectorStart + selector.length);
  if (selectorStart === -1 || blockStart === -1) return '';

  let depth = 0;
  for (let index = blockStart; index < source.length; index++) {
    if (source[index] === '{') depth += 1;
    if (source[index] !== '}') continue;
    depth -= 1;
    if (depth === 0) return source.slice(blockStart + 1, index);
  }

  return '';
}

describe('mobile login page', () => {
  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    LoginPage = (await import('../login.vue')).default;
  });

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    user.username = '';
    user.password = '';
    isSupported.value = true;
    hasKnownPasskey.value = false;
    login.mockResolvedValue(undefined);
    loginWithPasskey.mockResolvedValue(true);
    vi.mocked(useAuth).mockReturnValue({
      user,
      login,
    } as unknown as ReturnType<typeof useAuth>);
    vi.mocked(usePasskey).mockReturnValue({
      isSupported,
      hasKnownPasskey,
      loginWithPasskey,
    } as unknown as ReturnType<typeof usePasskey>);
  });

  it('should use native form submission when the password form is submitted', async () => {
    const wrapper = mountLogin();

    await wrapper.get('form').trigger('submit');

    expect(login).toHaveBeenCalledTimes(1);
  });

  it('should ignore repeated password submission when login is pending', async () => {
    let finishLogin: (() => void) | undefined;
    login.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          finishLogin = resolve;
        })
    );
    const wrapper = mountLogin();

    await wrapper.get('form').trigger('submit');
    await wrapper.get('form').trigger('submit');

    expect(login).toHaveBeenCalledTimes(1);
    finishLogin?.();
    await flushPromises();
  });

  it('should keep password and passkey actions distinct when both are available', () => {
    const wrapper = mountLogin();

    expect({
      passkey: wrapper.get('.passkey-btn').attributes('type'),
      password: wrapper.get('.ab-btn').attributes('type'),
    }).toEqual({ passkey: 'button', password: 'submit' });
  });

  it('should request silent passkey login when a known credential is available', async () => {
    hasKnownPasskey.value = true;
    user.username = 'admin';

    mountLogin();
    await flushPromises();

    expect(loginWithPasskey).toHaveBeenCalledWith('admin', { silent: true });
  });

  it('should ignore repeated passkey requests when authentication is pending', async () => {
    let finishPasskeyLogin: ((result: boolean) => void) | undefined;
    loginWithPasskey.mockImplementation(
      () =>
        new Promise<boolean>((resolve) => {
          finishPasskeyLogin = resolve;
        })
    );
    const wrapper = mountLogin();

    await wrapper.get('.passkey-btn').trigger('click');
    await wrapper.get('.passkey-btn').trigger('click');

    expect(loginWithPasskey).toHaveBeenCalledTimes(1);
    finishPasskeyLogin?.(true);
    await flushPromises();
  });

  it('should not auto-prompt passkey when logout suppresses the next prompt', async () => {
    hasKnownPasskey.value = true;
    sessionStorage.setItem('suppressPasskeyAutoPrompt', '1');

    mountLogin();
    await flushPromises();

    expect(loginWithPasskey).not.toHaveBeenCalled();
  });

  it('should use a safe scrollable viewport below the phone breakpoint', () => {
    const pageRule = scssBlock(phoneStyles(), '.page-login');

    expect(pageRule).toMatch(
      /height:\s*100vh;[\s\S]*?height:\s*100dvh;[\s\S]*?overflow-y:\s*auto;[\s\S]*?env\(safe-area-inset-top,\s*0px\)/
    );
  });

  it('should remove decorative card effects below the phone breakpoint', () => {
    const styles = phoneStyles();
    const backgroundRule = scssBlock(styles, '.login-bg');
    const cardRule = scssBlock(styles, '.login-card');

    expect({
      cardIsFlat:
        cardRule.includes('backdrop-filter: none') &&
        cardRule.includes('box-shadow: none'),
      decorationIsHidden: backgroundRule.includes('display: none'),
    }).toEqual({ cardIsFlat: true, decorationIsHidden: true });
  });

  it('should keep login controls touch-safe below the phone breakpoint', () => {
    const styles = phoneStyles();
    const inputRule = scssBlock(styles, '.login-input');
    const passkeyRule = scssBlock(styles, '.passkey-btn');

    expect({
      inputIsTouchSafe:
        inputRule.includes('min-height: var(--touch-target)') &&
        inputRule.includes('font-size: 16px'),
      passkeyIsTouchSafe: passkeyRule.includes(
        'min-height: var(--touch-target)'
      ),
    }).toEqual({ inputIsTouchSafe: true, passkeyIsTouchSafe: true });
  });
});
