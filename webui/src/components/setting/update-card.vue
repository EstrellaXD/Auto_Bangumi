<script lang="ts" setup>
import { NProgress, NSpin, NSwitch, NTag } from 'naive-ui';
import { useConfirm } from '@/hooks/useConfirm';
import type { UpdateChannel, UpdateInfo } from '#/update';

const { t } = useMyI18n();
const { confirm } = useConfirm();

async function onApplyClick() {
  const ok = await confirm({
    title: t('update.confirm_title'),
    body: t('update.confirm_body'),
    confirmText: t('update.update_now'),
  });
  if (ok) onApply();
}

async function onRollbackClick() {
  const ok = await confirm({
    title: t('update.rollback'),
    body: t('update.rollback_confirm'),
    confirmText: t('update.rollback'),
    danger: true,
  });
  if (ok) onRollback();
}
const message = useMessage();
const { updateData } = useEventStream();
const { version } = useAppInfo();
const configStore = useConfigStore();
const { getConfig } = configStore;
const { config, isDirty } = storeToRefs(configStore);

const info = ref<UpdateInfo | null>(null);
const channel = ref<UpdateChannel>(config.value.update?.channel ?? 'stable');
const autoCheck = ref(true);

// 渠道/自动检查改动直接写回配置（不经过设置页的“保存并重启”流程，
// 也不触发重启）。设置页有未保存修改时只改内存值，随用户的保存一起提交。
async function persistUpdateSetting(patch: {
  channel?: UpdateChannel;
  auto_check?: boolean;
}) {
  const hasPendingEdits = isDirty.value;
  if (!hasPendingEdits) await getConfig();
  config.value.update = { ...config.value.update, ...patch };
  if (!hasPendingEdits) {
    await apiConfig.updateConfig(JSON.parse(JSON.stringify(config.value)));
    await getConfig();
  }
}

function onChannelToggle(beta: boolean) {
  channel.value = beta ? 'beta' : 'stable';
  persistUpdateSetting({ channel: channel.value });
}

function onAutoCheckToggle(value: boolean) {
  autoCheck.value = value;
  persistUpdateSetting({ auto_check: value });
}
const checking = ref(false);
const applying = ref(false);
const restarting = ref(false);
const restartTimedOut = ref(false);

let pollTimer: ReturnType<typeof setInterval> | undefined;
let timeoutTimer: ReturnType<typeof setTimeout> | undefined;

const currentVersion = computed(
  () => info.value?.current || version.value || '-'
);
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

// 上次检查完成的时刻；用户主动点检查时每次刷新，给出"确实检查过了"的反馈。
const lastCheckedAt = ref<Date | null>(null);
const lastCheckedLabel = computed(() =>
  lastCheckedAt.value ? lastCheckedAt.value.toLocaleTimeString() : ''
);

// userInitiated：来自“检查更新”按钮。强制绕过后端 15 分钟缓存并弹出主动反馈；
// 挂载时的自动检查走缓存、保持安静。
async function onCheck(userInitiated = false) {
  checking.value = true;
  try {
    const res = await apiUpdate.check(channel.value, userInitiated);
    info.value = res;
    lastCheckedAt.value = new Date();
    if (res.error) {
      // 展示后端的具体原因（如 GitHub 限流 / 无匹配 Release），而非泛化文案
      message.error(`${t('update.check_failed')}: ${res.error}`);
    } else if (userInitiated) {
      if (res.has_update) {
        message.info(t('update.found_new', { version: res.latest ?? '' }));
      } else {
        message.success(t('update.up_to_date'));
      }
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

onMounted(async () => {
  // 日志页不一定加载过配置：先取一次，避免读到 initConfig 默认值
  if (!isDirty.value) {
    try {
      await getConfig();
    } catch {
      // 拉取失败时按默认行为处理
    }
  }
  channel.value = config.value.update?.channel ?? 'stable';
  autoCheck.value = config.value.update?.auto_check !== false;
  if (autoCheck.value) {
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
            :aria-label="$t('update.channel')"
            @update:value="onChannelToggle"
          />
          <span :class="{ dim: channel === 'stable' }">
            {{ $t('update.channel_beta') }}
          </span>
        </div>
      </div>

      <!-- 自动检查 -->
      <div class="update-row">
        <span class="update-key">{{ $t('update.auto_check') }}</span>
        <NSwitch
          :value="autoCheck"
          :disabled="applying || restarting"
          :aria-label="$t('update.auto_check')"
          @update:value="onAutoCheckToggle"
        />
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

      <!-- 上次检查时间：给"检查更新"一个可见的状态变化 -->
      <p v-if="lastCheckedLabel" class="update-checked">
        {{ $t('update.last_checked', { time: lastCheckedLabel }) }}
      </p>

      <!-- 需要 restart: unless-stopped 的说明 -->
      <p class="update-note">{{ $t('update.restart_note') }}</p>

      <!-- 操作按钮 -->
      <div class="update-actions">
        <ab-button
          size="sm"
          variant="secondary"
          :loading="checking"
          :disabled="applying || restarting"
          @click="onCheck(true)"
        >
          {{ checking ? $t('update.checking') : $t('update.check') }}
        </ab-button>

        <ab-button
          variant="primary"
          size="sm"
          :disabled="!hasUpdate || applying || restarting"
          @click="onApplyClick"
        >
          {{ $t('update.update_now') }}
        </ab-button>

        <ab-button
          v-if="canRollback"
          variant="danger"
          size="sm"
          :disabled="applying || restarting"
          @click="onRollbackClick"
        >
          {{ $t('update.rollback') }}
        </ab-button>
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
.update-warn,
.update-checked {
  font-size: 12px;
  margin: 0;
}

.update-checked {
  color: var(--color-text-muted);
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
