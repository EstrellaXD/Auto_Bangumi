<script lang="ts" setup>
import { NInput } from 'naive-ui';
import type { LLMAuthChallenge } from '@/api/llm';
import AbModal from '@/components/basic/ab-modal.vue';

const props = defineProps<{
  show: boolean;
  providerId: string;
  displayName: string;
}>();

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
  (e: 'connected'): void;
}>();

const { t } = useMyI18n();
const message = useMessage();

const challenge = ref<LLMAuthChallenge | null>(null);
const loading = ref(false);
const pastedCode = ref('');
let pollTimer: ReturnType<typeof setInterval> | undefined;

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = undefined;
  }
}

function close() {
  stopPolling();
  challenge.value = null;
  pastedCode.value = '';
  emit('update:show', false);
}

function onShowUpdate(show: boolean) {
  if (!show) close();
}

async function begin() {
  loading.value = true;
  try {
    challenge.value = await apiLLM.beginAuth(props.providerId);
    if (challenge.value.method === 'device_code') startPolling();
  } catch {
    message.error(t('config.llm_set.auth_failed'));
    close();
  } finally {
    loading.value = false;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const status = await apiLLM.getAuthStatus(props.providerId);
      if (status.connected) {
        stopPolling();
        message.success(
          t('config.llm_set.connected_as', { account: status.account_label })
        );
        emit('connected');
        close();
      }
    } catch {
      // 轮询失败静默重试
    }
  }, 3000);
}

// redirect_paste：用户在自己设备打开授权链接，把回调 code/URL 粘回来
async function submitCode() {
  if (!challenge.value) return;
  loading.value = true;
  try {
    const res = await apiLLM.completeAuth(props.providerId, {
      state: challenge.value.state,
      code: pastedCode.value.trim(),
    });
    message.success(
      t('config.llm_set.connected_as', { account: res.account_label })
    );
    emit('connected');
    close();
  } catch {
    message.error(t('config.llm_set.auth_failed'));
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.show,
  (show) => {
    if (show) begin();
    else stopPolling();
  }
);

onUnmounted(stopPolling);
</script>

<template>
  <AbModal
    :show="show"
    desktop-max-width="460px"
    size="sm"
    :title="`${t('config.llm_set.connect')} · ${displayName}`"
    @update:show="onShowUpdate"
  >
    <div v-if="challenge" class="auth-body">
      <template v-if="challenge.method === 'device_code'">
        <p class="auth-step">{{ t('config.llm_set.auth_device_hint') }}</p>
        <a
          v-if="challenge.verification_uri"
          :href="challenge.verification_uri"
          target="_blank"
          rel="noopener"
          class="auth-link"
          >{{ challenge.verification_uri }}</a
        >
        <div class="auth-code">{{ challenge.user_code }}</div>
        <p class="auth-pending">{{ t('config.llm_set.auth_pending') }}</p>
      </template>

      <template v-else>
        <p class="auth-step">{{ t('config.llm_set.auth_open_link') }}</p>
        <a
          v-if="challenge.authorize_url"
          :href="challenge.authorize_url"
          target="_blank"
          rel="noopener"
          class="auth-link"
          >{{ challenge.authorize_url }}</a
        >
        <NInput
          v-model:value="pastedCode"
          class="auth-code-input"
          type="textarea"
          :rows="2"
          :placeholder="t('config.llm_set.auth_paste_code')"
        />
        <ab-button
          class="auth-submit"
          variant="primary"
          :loading="loading"
          :disabled="!pastedCode.trim()"
          @click="submitCode"
          >{{ t('config.llm_set.connect') }}</ab-button
        >
      </template>
    </div>
    <div v-else class="auth-body auth-loading">
      {{ t('config.llm_set.auth_pending') }}
    </div>
  </AbModal>
</template>

<style lang="scss" scoped>
.auth-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.auth-step {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.auth-link {
  font-size: 13px;
  color: var(--color-primary);
  word-break: break-all;
}

.auth-code {
  font-family: var(--font-mono, monospace);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-align: center;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.auth-pending {
  font-size: 12px;
  color: var(--color-text-muted);
}

.auth-loading {
  color: var(--color-text-muted);
  font-size: 13px;
}

@media screen and (max-width: 639px) {
  .auth-code-input {
    min-height: var(--touch-target);
  }

  .auth-submit {
    min-height: var(--touch-target);
  }
}
</style>
