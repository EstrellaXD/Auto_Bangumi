<script lang="ts" setup>
import { Fingerprint } from '@icon-park/vue-next';

definePage({
  name: 'Login',
});

const { user, login } = useAuth();
const { isSupported, loginWithPasskey } = usePasskey();

const isPasskeyLoading = ref(false);

async function handlePasskeyLogin() {
  if (!user.username) {
    const message = useMessage();
    const { t } = useMyI18n();
    message.warning(t('notify.please_enter', [t('login.username')]));
    return;
  }

  isPasskeyLoading.value = true;
  try {
    await loginWithPasskey(user.username);
  } finally {
    isPasskeyLoading.value = false;
  }
}
</script>

<template>
  <div class="page-login">
    <ab-container :title="$t('login.title')" class="login-card">
      <div class="login-form">
        <ab-label :label="$t('login.username')">
          <input
            v-model="user.username"
            type="text"
            placeholder="username"
            class="login-input"
          />
        </ab-label>

        <ab-label :label="$t('login.password')">
          <input
            v-model="user.password"
            type="password"
            placeholder="password"
            class="login-input"
            @keyup.enter="login"
          />
        </ab-label>

        <div class="divider"></div>

        <div class="login-actions">
          <ab-button
            v-if="isSupported"
            size="small"
            type="secondary"
            :disabled="isPasskeyLoading"
            @click="handlePasskeyLogin"
          >
            <Fingerprint size="16" />
            {{ $t('login.passkey_btn') }}
          </ab-button>
          <div v-else></div>
          <ab-button size="small" @click="login">
            {{ $t('login.login_btn') }}
          </ab-button>
        </div>
      </div>
    </ab-container>
  </div>
</template>

<style lang="scss" scoped>
.page-login {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
}

.login-card {
  width: 365px;
  max-width: 90%;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.login-input {
  outline: none;
  min-width: 0;
  width: 200px;
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  text-align: right;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
  }

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px rgba(108, 74, 182, 0.2);
  }

  &::placeholder {
    color: var(--color-text-muted);
  }
}

.divider {
  width: 100%;
  height: 1px;
  background: var(--color-border);
}

.login-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
