<script lang="ts" setup>
import { NPopover } from 'naive-ui';
import { createReusableTemplate } from '@vueuse/core';
import { Bell, CircleAlert, CircleX, Info, Trash } from '@lucide/vue';
import type { InboxMessage } from '@/api/notification';
import { relativeTime } from '@/utils/relative-time';

const { t } = useMyI18n();
const router = useRouter();
const store = useNotificationStore();
const { messages, unreadCount, panelOpen } = storeToRefs(store);
// 手机上面板放进底部抽屉：贴着铃铛的浮层在窄屏两侧都放不下
const { isMobile } = useBreakpointQuery();
const [DefinePanelBody, PanelBody] = createReusableTemplate();

// 点条目跳转的目标页面；未列出的 kind 不跳转
const KIND_ROUTES: Record<string, string> = {
  update_available: '/config',
  update_applied: '/config',
  update_failed: '/config',
  downloader_unavailable: '/config',
  rss_failure: '/rss',
  offset_review: '/bangumi',
  download_failure: '/bangumi',
  rename_conflict: '/downloader',
  rename_skipped: '/downloader',
};

const SEVERITY_ICONS = {
  error: CircleX,
  warning: CircleAlert,
  info: Info,
} as const;

const confirmClear = ref(false);
const bell = useTemplateRef<HTMLButtonElement>('bell');

// 打开时拉取列表，关闭时复位确认态。
function onShowChange(open: boolean) {
  if (open) {
    store.fetchMessages();
  } else {
    confirmClear.value = false;
  }
  panelOpen.value = open;
}

// NPopover 不处理 Esc：关闭后把焦点还给铃铛
function closeByEsc() {
  onShowChange(false);
  bell.value?.focus();
}

function severityIcon(msg: InboxMessage) {
  return SEVERITY_ICONS[msg.severity] ?? Info;
}

function onItemClick(msg: InboxMessage) {
  store.markRead(msg.id);
  const route = KIND_ROUTES[msg.kind];
  if (route) {
    onShowChange(false);
    router.push(route);
  }
}

function onClearClick() {
  if (!confirmClear.value) {
    confirmClear.value = true;
    return;
  }
  confirmClear.value = false;
  store.clearAll();
}
</script>

<template>
  <div class="notification-center">
    <DefinePanelBody>
      <div class="notification-head">
        <span class="notification-head-title">
          {{ $t('notifications.title') }}
          <template v-if="unreadCount > 0">
            · {{ $t('notifications.unread', { n: unreadCount }) }}
          </template>
        </span>
        <div class="notification-head-actions">
          <ab-button
            v-if="unreadCount > 0"
            variant="ghost"
            size="sm"
            @click="store.markAllRead()"
          >
            {{ $t('notifications.mark_all_read') }}
          </ab-button>
          <ab-button
            v-if="messages.length > 0"
            variant="danger"
            size="sm"
            @click="onClearClick"
          >
            {{
              confirmClear
                ? $t('notifications.clear_confirm')
                : $t('notifications.clear_all')
            }}
          </ab-button>
        </div>
      </div>

      <div v-if="messages.length === 0" class="notification-empty">
        {{ $t('notifications.empty') }}
      </div>

      <div v-else class="notification-list">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="notification-item"
          :class="{ 'notification-item--unread': !msg.read }"
          role="button"
          tabindex="0"
          @click="onItemClick(msg)"
          @keydown.enter="onItemClick(msg)"
        >
          <div class="notification-sev" :class="`is-${msg.severity}`">
            <Component :is="severityIcon(msg)" :size="14" />
          </div>
          <div class="notification-content">
            <div class="notification-title">
              {{ store.titleOf(msg) }}
              <span v-if="msg.count > 1" class="notification-count">×{{ msg.count }}</span>
            </div>
            <div class="notification-body">
              {{ store.bodyOf(msg) }}
            </div>
            <div class="notification-meta">
              {{ relativeTime(t, msg.updated_at) }}
            </div>
          </div>
          <ab-icon-button
            size="sm"
            class="notification-delete"
            :label="$t('notifications.delete')"
            @click.stop="store.remove(msg.id)"
          >
            <Trash :size="13" />
          </ab-icon-button>
        </div>
      </div>
    </DefinePanelBody>

    <NPopover
      trigger="click"
      placement="bottom-end"
      raw
      :show-arrow="false"
      :show="panelOpen && !isMobile"
      @update:show="onShowChange"
    >
      <template #trigger>
        <button
          ref="bell"
          type="button"
          class="notification-bell"
          :aria-label="$t('notifications.title')"
          aria-haspopup="dialog"
          :aria-expanded="panelOpen"
          @keydown.esc="closeByEsc"
        >
          <Bell :size="18" />
          <ab-badge class="notification-badge" :count="unreadCount" />
        </button>
      </template>

      <div class="notification-panel" @keydown.esc="closeByEsc">
        <PanelBody />
      </div>
    </NPopover>

    <ab-bottom-sheet
      v-if="isMobile"
      class="notification-sheet"
      :show="panelOpen"
      :show-close="false"
      @update:show="onShowChange"
    >
      <PanelBody />
    </ab-bottom-sheet>
  </div>
</template>

<!-- 不加 scoped：面板由 NPopover 传送到 body，trigger 插槽也经 naive-ui 克隆渲染，
     scoped 选择器不可靠。所有类名以 notification- 前缀隔离，避免全局冲突。 -->
<style lang="scss">
.notification-center {
  position: relative;
  display: flex;
  align-items: center;
}

// 与 ab-status-bar 的 .status-bar-btn 保持一致
.notification-bell {
  position: relative;
  cursor: pointer;
  user-select: none;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast), transform var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  min-width: 36px;
  min-height: 36px;
  padding: 6px;
  border-radius: var(--radius-sm);
  font-size: 18px;

  // 与 ab-status-bar 保持一致：仅触屏放大命中区域，桌面保持紧凑。
  @include forTouch {
    min-width: var(--touch-target);
    min-height: var(--touch-target);
  }

  &:hover {
    color: var(--color-primary);
    transform: scale(1.1);
  }

  &:active {
    transform: scale(0.95);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.notification-badge {
  position: absolute;
  top: 0;
  right: 0;
  pointer-events: none;
}

.notification-sheet .ab-bottom-sheet__content {
  padding: 0;
}

.notification-panel {
  width: min(340px, calc(100vw - 24px));
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: notification-dropdown-in 150ms ease-out;
  transform-origin: top right;
}

@keyframes notification-dropdown-in {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.notification-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border);
}

.notification-head-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.notification-head-actions {
  display: flex;
  gap: 4px;
}

.notification-empty {
  padding: 32px 14px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}

.notification-list {
  max-height: min(420px, 60vh);
  overflow-y: auto;
}

.notification-item {
  display: flex;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background-color var(--transition-fast);

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: var(--color-surface-hover);

    .notification-delete {
      opacity: 1;
    }
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  &--unread {
    box-shadow: inset 3px 0 0 var(--color-primary);
  }

  &:not(.notification-item--unread) {
    opacity: 0.6;
  }
}

.notification-sev {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  margin-top: 2px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;

  &.is-error {
    color: var(--color-danger, #ef4444);
    background: color-mix(in srgb, var(--color-danger) 14%, transparent);
  }

  &.is-warning {
    color: var(--color-warning, #f59e0b);
    background: color-mix(in srgb, var(--color-warning) 16%, transparent);
  }

  &.is-info {
    color: var(--color-primary);
    background: var(--color-primary-light);
  }
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.notification-count {
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 10.5px;
  font-weight: 700;
  border-radius: 8px;
  padding: 0 6px;
}

.notification-body {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow-wrap: anywhere;
}

.notification-meta {
  margin-top: 2px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.notification-delete {
  flex-shrink: 0;
  align-self: flex-start;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 4px;
  border-radius: var(--radius-sm);
  opacity: 0;
  transition: opacity var(--transition-fast), color var(--transition-fast);

  &:hover {
    color: var(--color-danger, #ef4444);
  }

  &:focus-visible {
    opacity: 1;
    outline: 2px solid var(--color-primary);
  }

  @include forTouch {
    opacity: 1;
  }
}
</style>
