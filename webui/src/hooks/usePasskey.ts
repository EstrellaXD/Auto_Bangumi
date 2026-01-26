import { createSharedComposable } from '@vueuse/core';
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
  const isSupported = ref(false);

  // 检测浏览器支持
  onMounted(() => {
    isSupported.value = isWebAuthnSupported();
  });

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
  async function loginWithPasskey(username?: string): Promise<boolean> {
    try {
      await webauthnLogin(username);
      isLoggedIn.value = true;
      message.success(t('notify.login_success'));
      return true;
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'status' in error) {
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

    // 方法
    loadPasskeys,
    addPasskey,
    loginWithPasskey,
    deletePasskey,
  };
});
