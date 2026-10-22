<script lang="ts" setup>
import type { LLMAuthChallenge } from '@/api/llm';

const props = defineProps<{
  providerId: string;
  displayName: string;
}>();

const emit = defineEmits<{
  (e: 'connected'): void;
}>();

const show = defineModel<boolean>('show', { required: true });

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

// 内容留到下次打开再清空，弹窗淡出时不切换成等待文字
function close() {
  stopPolling();
  show.value = false;
}

async function begin() {
  challenge.value = null;
  pastedCode.value = '';
  loading.value = true;
  try {
    const result = await apiLLM.beginAuth(props.providerId);
    // 请求返回前弹窗已关闭：丢弃结果，不在隐藏的弹窗里轮询
    if (!show.value) return;
    challenge.value = result;
    if (result.method === 'device_code') startPolling();
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

// ab-modal 的 X/遮罩/Esc/抽屉下滑只改 show，关闭时在这里统一清理
watch(show, (visible) => {
  if (visible) begin();
  else close();
});

onUnmounted(stopPolling);
</script>

<template>
  <ab-modal
    v-model:show="show"
    size="sm"
    :title="`${t('config.llm_set.connect')} · ${displayName}`"
  >
    <div v-if="challenge" class="auth-body">
      <template v-if="challenge.method === 'device_code'">
        <p class="auth-step">
          {{ t('config.llm_set.auth_device_hint') }}
        </p>
        <a
          v-if="challenge.verification_uri"
          :href="challenge.verification_uri"
          target="_blank"
          rel="noopener"
          class="auth-link"
        >{{ challenge.verification_uri }}</a>
        <div class="auth-code">
          {{ challenge.user_code }}
        </div>
        <p class="auth-pending">
          {{ t('config.llm_set.auth_pending') }}
        </p>
      </template>

      <template v-else>
        <p class="auth-step">
          {{ t('config.llm_set.auth_open_link') }}
        </p>
        <a
          v-if="challenge.authorize_url"
          :href="challenge.authorize_url"
          target="_blank"
          rel="noopener"
          class="auth-link"
        >{{ challenge.authorize_url }}</a>
        <textarea
          v-model="pastedCode"
          class="auth-textarea"
          rows="2"
          :aria-label="t('config.llm_set.auth_paste_code')"
          :placeholder="t('config.llm_set.auth_paste_code')"
        />
      </template>
    </div>
    <div v-else class="auth-body auth-loading">
      {{ t('config.llm_set.auth_pending') }}
    </div>

    <template #footer>
      <ab-button size="sm" @click="close">
        {{ t('config.cancel') }}
      </ab-button>
      <ab-button
        v-if="challenge && challenge.method !== 'device_code'"
        size="sm"
        variant="primary"
        :loading="loading"
        :disabled="!pastedCode.trim()"
        @click="submitCode"
      >
        {{ t('config.llm_set.connect') }}
      </ab-button>
    </template>
  </ab-modal>
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

.auth-textarea {
  // Soft Ink 填充式多行输入（与 config-notification 的 .field-textarea 一致）
  width: 100%;
  padding: 8px 11px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: var(--color-surface-2);
  color: var(--color-text);
  outline: none;
  resize: none;
  font-family: var(--font-mono);
  font-size: 13px;
  transition: border-color var(--transition-fast),
    background-color var(--transition-fast), box-shadow var(--transition-fast);

  &:focus {
    background: var(--color-surface);
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-primary-alpha);
  }
}

.auth-pending {
  font-size: 12px;
  color: var(--color-text-muted);
}

.auth-loading {
  color: var(--color-text-muted);
  font-size: 13px;
}
</style>
