<script lang="ts" setup>
import { NButton, NPopconfirm, NProgress, NSpin, NSwitch, NTag } from 'naive-ui';
import type { UpdateChannel, UpdateInfo } from '#/update';

const { t } = useMyI18n();
const message = useMessage();
const { updateData } = useEventStream();
const { version } = useAppInfo();
const { config } = storeToRefs(useConfigStore());

const info = ref<UpdateInfo | null>(null);
const channel = ref<UpdateChannel>(config.value.update?.channel ?? 'stable');
const checking = ref(false);
const applying = ref(false);
const restarting = ref(false);
const restartTimedOut = ref(false);

let pollTimer: ReturnType<typeof setInterval> | undefined;
let timeoutTimer: ReturnType<typeof setTimeout> | undefined;

const currentVersion = computed(() => info.value?.current || version.value || '-');
const hasUpdate = computed(() => info.value?.has_update === true);
const canRollback = computed(() => info.value?.can_rollback === true);
const appliedVersion = computed(() => info.value?.applied_version || '');

// SSE 推送的进度：apply 期间用来驱动进度条与阶段文案。
const progress = computed(() => updateData.value);
const progressPercent = computed(() => progress.value?.percent ?? 0);
const isDownloading = computed(() => progress.value?.phase === 'downloading');

const phaseLabel = computed(() => {
  const phase = progress.value?.phase;
  const map: Record<string, string> = {
    downloading: t('update.phase_downloading'),
    verifying: t('update.phase_verifying'),
    unpacking: t('update.phase_unpacking'),
    promoting: t('update.phase_promoting'),
  };
  return phase ? map[phase] ?? '' : '';
});

/**
 * 极简且防 XSS 的 Release 说明渲染：先转义所有 HTML，再对少量 markdown 语法
 * 做替换（标题/加粗/行内代码/链接/无序列表/换行）。输入来自项目固定的 GitHub
 * Release，但仍先转义以确保安全。
 */
function renderNotes(md: string): string {
  if (!md) return '';
  const escaped = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return escaped
    .replace(/^###?\s?#*\s*(.*)$/gm, '<strong>$1</strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+?)`/g, '<code>$1</code>')
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    )
    .replace(/^[-*]\s+(.*)$/gm, '• $1')
    .replace(/\n/g, '<br>');
}

const notesHtml = computed(() => renderNotes(info.value?.notes ?? ''));

async function onCheck() {
  checking.value = true;
  try {
    const res = await apiUpdate.check(channel.value);
    info.value = res;
    if (res.error) {
      message.error(t('update.check_failed'));
    }
  } catch {
    // axios 拦截器已提示网络错误
  } finally {
    checking.value = false;
  }
}

function startRestartWatch() {
  restarting.value = true;
  restartTimedOut.value = false;
  let sawDown = false;
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      await apiProgram.status();
      // 重启完成：先经历一次不可达（sawDown）再恢复，才判定已回来。
      if (sawDown) {
        clearInterval(pollTimer);
        clearTimeout(timeoutTimer);
        window.location.reload();
      }
    } catch {
      sawDown = true;
    }
  }, 3000);
  // 超时仍未恢复：提示需要 restart: unless-stopped 或手动重启。
  clearTimeout(timeoutTimer);
  timeoutTimer = setTimeout(() => {
    restartTimedOut.value = true;
  }, 60000);
}

async function onApply() {
  applying.value = true;
  try {
    const res = await apiUpdate.apply(channel.value);
    if (res.success && res.restart_required) {
      startRestartWatch();
    } else {
      message.error(res.message || t('update.failed'));
      applying.value = false;
    }
  } catch {
    applying.value = false;
  }
}

async function onRollback() {
  applying.value = true;
  try {
    const res = await apiUpdate.rollback();
    if (res.success && res.restart_required) {
      startRestartWatch();
    } else {
      message.error(res.message || t('update.failed'));
      applying.value = false;
    }
  } catch {
    applying.value = false;
  }
}

// 切换渠道后若已检查过，则自动用新渠道重新检查。
watch(channel, () => {
  if (info.value) onCheck();
});

onMounted(() => {
  if (config.value.update?.auto_check !== false) {
    onCheck();
  }
});

onBeforeUnmount(() => {
  clearInterval(pollTimer);
  clearTimeout(timeoutTimer);
});
</script>

<template>
  <ab-container :title="$t('update.title')">
    <div class="update-card">
      <!-- 版本信息 -->
      <div class="update-row">
        <span class="update-key">{{ $t('update.current_version') }}</span>
        <span class="update-val">{{ currentVersion }}</span>
      </div>
      <div v-if="info?.latest" class="update-row">
        <span class="update-key">{{ $t('update.latest_version') }}</span>
        <span class="update-val">
          {{ info.latest }}
          <NTag v-if="hasUpdate" type="success" size="small" round>
            {{ $t('update.update_available') }}
          </NTag>
        </span>
      </div>

      <p v-if="appliedVersion" class="update-hint">
        {{ $t('update.applied_overlay', { version: appliedVersion }) }}
      </p>

      <!-- 渠道选择 -->
      <div class="update-row">
        <span class="update-key">{{ $t('update.channel') }}</span>
        <div class="update-channel">
          <span :class="{ dim: channel === 'beta' }">
            {{ $t('update.channel_stable') }}
          </span>
          <NSwitch
            :value="channel === 'beta'"
            :disabled="applying || restarting"
            @update:value="(v: boolean) => (channel = v ? 'beta' : 'stable')"
          />
          <span :class="{ dim: channel === 'stable' }">
            {{ $t('update.channel_beta') }}
          </span>
        </div>
      </div>

      <!-- 状态提示 -->
      <p v-if="info && !info.error && !hasUpdate" class="update-ok">
        {{ $t('update.up_to_date') }}
      </p>

      <!-- Release 说明 -->
      <div v-if="hasUpdate && notesHtml" class="update-notes-wrap">
        <div class="update-key">{{ $t('update.release_notes') }}</div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="update-notes" v-html="notesHtml"></div>
      </div>

      <!-- 进度条（apply 期间） -->
      <div v-if="applying && progress && !restarting" class="update-progress">
        <NProgress
          type="line"
          :percentage="isDownloading ? progressPercent : 100"
          :processing="!isDownloading"
          :indicator-placement="isDownloading ? 'outside' : 'inside'"
        />
        <div class="update-phase">{{ phaseLabel || progress.message }}</div>
      </div>

      <!-- 重启中 -->
      <div v-if="restarting" class="update-restart">
        <NSpin size="small" />
        <span>{{ $t('update.restarting') }}</span>
      </div>
      <p v-if="restartTimedOut" class="update-warn">
        {{ $t('update.restart_timeout') }}
      </p>

      <!-- 需要 restart: unless-stopped 的说明 -->
      <p class="update-note">{{ $t('update.restart_note') }}</p>

      <!-- 操作按钮 -->
      <div class="update-actions">
        <NButton
          size="small"
          :loading="checking"
          :disabled="applying || restarting"
          @click="onCheck"
        >
          {{ checking ? $t('update.checking') : $t('update.check') }}
        </NButton>

        <NPopconfirm
          :positive-text="$t('update.update_now')"
          @positive-click="onApply"
        >
          <template #trigger>
            <NButton
              type="primary"
              size="small"
              :disabled="!hasUpdate || applying || restarting"
            >
              {{ $t('update.update_now') }}
            </NButton>
          </template>
          <div class="update-confirm">
            <strong>{{ $t('update.confirm_title') }}</strong>
            <div>{{ $t('update.confirm_body') }}</div>
          </div>
        </NPopconfirm>

        <NPopconfirm
          v-if="canRollback"
          :positive-text="$t('update.rollback')"
          @positive-click="onRollback"
        >
          <template #trigger>
            <NButton
              type="warning"
              size="small"
              :disabled="applying || restarting"
            >
              {{ $t('update.rollback') }}
            </NButton>
          </template>
          {{ $t('update.rollback_confirm') }}
        </NPopconfirm>
      </div>
    </div>
  </ab-container>
</template>

<style lang="scss" scoped>
.update-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.update-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.update-key {
  font-size: 13px;
  color: var(--color-text-muted);
}

.update-val {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text);
}

.update-channel {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;

  .dim {
    color: var(--color-text-muted);
  }
}

.update-hint,
.update-ok,
.update-note,
.update-warn {
  font-size: 12px;
  margin: 0;
}

.update-hint {
  color: var(--color-primary);
}

.update-ok {
  color: var(--color-text-secondary);
}

.update-note {
  color: var(--color-text-muted);
}

.update-warn {
  color: var(--color-warning);
}

.update-notes-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.update-notes {
  max-height: 200px;
  overflow: auto;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  word-break: break-word;

  :deep(code) {
    padding: 1px 4px;
    border-radius: 3px;
    background: var(--color-border);
    font-size: 11px;
  }
}

.update-progress {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.update-phase {
  font-size: 12px;
  color: var(--color-text-muted);
}

.update-restart {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-primary);
}

.update-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.update-confirm {
  max-width: 260px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}
</style>
