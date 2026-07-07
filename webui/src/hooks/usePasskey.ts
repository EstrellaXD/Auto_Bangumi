import { createSharedComposable, useLocalStorage } from '@vueuse/core';
import { router } from '@/router';
import { apiPasskey } from '@/api/passkey';
import {
  isWebAuthnSupported,
  registerPasskey,
  loginWithPasskey as webauthnLogin,
} from '@/services/webauthn';
import type { PasskeyItem } from '#/passkey';

export const usePasskey = createSharedComposable(() => {
  const message = useMessage();
  const { t } = useMyI18n();
  const { isLoggedIn } = useAuth();

  // 状态
  const passkeys = ref<PasskeyItem[]>([]);
  const loading = ref(false);
  const isSupported = ref(isWebAuthnSupported());
  // 本浏览器成功注册/使用过 passkey 的标记：登录页据此自动弹出认证。
  // 浏览器无法在登录前查询设备上是否有可用凭证，只能靠本地记忆。
  const hasKnownPasskey = useLocalStorage('hasPasskey', false);

  // 加载 Passkey 列表
  async function loadPasskeys() {
    if (!isLoggedIn.value) return;

    try {
      loading.value = true;
      passkeys.value = await apiPasskey.list();
    } catch (error) {
      console.error('Failed to load passkeys:', error);
    } finally {
      loading.value = false;
    }
  }

  // 注册新 Passkey
  async function addPasskey(deviceName: string): Promise<boolean> {
    try {
      await registerPasskey(deviceName);
      hasKnownPasskey.value = true;
      message.success(t('passkey.register_success'));
      await loadPasskeys();
      return true;
    } catch (error: unknown) {
      // Don't show duplicate message if axios interceptor already handled it
      if (error && typeof error === 'object' && 'status' in error) {
        return false;
      }
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      message.error(`${t('passkey.register_failed')}: ${errorMessage}`);
      return false;
    }
  }

  // 使用 Passkey 登录
  // silent：登录页自动弹出的认证——用户取消/失败时静默回落到密码表单，
  // 不弹错误提示
  async function loginWithPasskey(
    username?: string,
    options: { silent?: boolean } = {}
  ): Promise<boolean> {
    try {
      await webauthnLogin(username);
      hasKnownPasskey.value = true;
      isLoggedIn.value = true;
      message.success(t('notify.login_success'));
      // 密码登录在 useAuth 里跳转；passkey 此前漏了这一步，导致登录成功
      // 却停留在登录页（#登录卡住不转跳）
      await router.replace({ name: 'Index' });
      return true;
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'status' in error) {
        // API 错误：axios 拦截器已提示，且不代表凭证失效
        return false;
      }
      if (options.silent && error instanceof DOMException) {
        // WebAuthn 仪式被取消/不可用（用户取消、设备上没有凭证、Safari
        // 的手势限制——浏览器刻意不区分这几种）。解除自动弹出记忆，
        // 避免每次打开登录页都弹一个注定失败的框；下次 passkey 登录
        // 成功会重新记住。
        hasKnownPasskey.value = false;
        return false;
      }
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      message.error(`${t('passkey.login_failed')}: ${errorMessage}`);
      return false;
    }
  }

  // 删除 Passkey
  async function deletePasskey(passkeyId: number): Promise<boolean> {
    try {
      await apiPasskey.delete({ passkey_id: passkeyId });
      message.success(t('passkey.delete_success'));
      await loadPasskeys();
      if (passkeys.value.length === 0) {
        hasKnownPasskey.value = false;
      }
      return true;
    } catch (error) {
      message.error(t('passkey.delete_failed'));
      return false;
    }
  }

  return {
    // 状态
    passkeys,
    loading,
    isSupported,
    hasKnownPasskey,

    // 方法
    loadPasskeys,
    addPasskey,
    loginWithPasskey,
    deletePasskey,
  };
});
