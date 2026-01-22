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
  <div wh-screen f-cer bg-page>
    <ab-container :title="$t('login.title')" w-365 max-w="90%">
      <div space-y-16>
        <ab-label :label="$t('login.username')">
          <input
            v-model="user.username"
            type="text"
            placeholder="username"
            ab-input
          />
        </ab-label>

        <ab-label :label="$t('login.password')">
          <input
            v-model="user.password"
            type="password"
            placeholder="password"
            ab-input
            @keyup.enter="login"
          />
        </ab-label>

        <div line></div>

        <div flex="~ justify-between items-center">
          <ab-button
            v-if="isSupported"
            size="small"
            type="secondary"
            :disabled="isPasskeyLoading"
            @click="handlePasskeyLogin"
          >
            <Fingerprint size="16" mr-4 />
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
