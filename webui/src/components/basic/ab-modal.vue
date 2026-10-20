<script lang="ts" setup>
import { X } from '@lucide/vue';
import { NModal } from 'naive-ui';
import AbBottomSheet from './ab-bottom-sheet.vue';
import AbIconButton from './ab-icon-button.vue';
import { useBreakpointQuery } from '@/hooks/useBreakpointQuery';

// 唯一的自适应弹窗组件（合并旧 ab-popup / ab-adaptive-modal）：
// 桌面居中对话框，移动端底部抽屉。naive-ui NModal 提供焦点陷阱与 Esc/遮罩关闭，
// 无 preset 时不带 aria，dialog 语义写在面板上。
const {
  title = '',
  size = 'md',
  closable = true,
  showClose = true,
  maxHeight = '85dvh',
  mobileFullscreen = false,
  avoidKeyboard = true,
} = defineProps<{
  title?: string;
  size?: 'sm' | 'md' | 'lg';
  /** false 时禁用遮罩点击/关闭按钮（用于流程中不可中断的弹窗） */
  closable?: boolean;
  /** 隐藏右上角 X（confirm 类弹窗：Esc/遮罩仍可关闭） */
  showClose?: boolean;
  maxHeight?: string;
  /** 移动端用整屏抽屉承载长表单 */
  mobileFullscreen?: boolean;
  /** 移动端软键盘出现时是否把抽屉整体上移 */
  avoidKeyboard?: boolean;
}>();

const emit = defineEmits<{ close: [] }>();

const show = defineModel<boolean>('show', { default: false });

const { isMobile } = useBreakpointQuery();
const titleId = useId();

function close() {
  if (!closable) return;
  show.value = false;
  emit('close');
}
</script>

<template>
  <!-- 移动端：底部抽屉 -->
  <AbBottomSheet
    v-if="isMobile"
    :show="show"
    :title="title"
    :closeable="closable"
    :show-close="showClose"
    :close-label="$t('common.close')"
    :max-height="maxHeight"
    :fullscreen="mobileFullscreen"
    :avoid-keyboard="avoidKeyboard"
    @update:show="show = $event"
    @close="emit('close')"
  >
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </AbBottomSheet>

  <!-- 桌面/平板：居中对话框 -->
  <NModal
    v-else
    :show="show"
    :mask-closable="closable"
    :close-on-esc="closable"
    @update:show="(value: boolean) => value || close()"
  >
    <div
      class="ab-modal-panel"
      :class="[
        `ab-modal-panel--${size}`,
        !$slots.default && 'ab-modal-panel--bare',
      ]"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="title ? titleId : undefined"
    >
      <header
        v-if="title || (closable && showClose)"
        class="ab-modal-header"
      >
        <h2 :id="titleId" class="ab-modal-title">
          {{ title }}
        </h2>
        <AbIconButton
          v-if="closable && showClose"
          class="ab-modal-close"
          size="sm"
          :label="$t('common.close')"
          @click="close"
        >
          <X :size="16" />
        </AbIconButton>
      </header>

      <div
        v-if="$slots.default"
        class="ab-modal-body"
        :style="{ maxHeight }"
      >
        <slot />
      </div>

      <footer v-if="$slots.footer" class="ab-modal-footer">
        <slot name="footer" />
      </footer>
    </div>
  </NModal>
</template>

<style lang="scss" scoped>
.ab-modal-panel {
  display: flex;
  flex-direction: column;
  // 原 wrapper 的 16px 留白；NModal 的滚动容器负责居中
  width: calc(100% - 32px);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;

  &--sm {
    max-width: 400px;
  }

  &--md {
    max-width: 520px;
  }

  &--lg {
    max-width: 680px;
  }

  // 无正文的紧凑形态（confirm）：头/脚之间没有 body，去掉多余分割线
  &--bare {
    .ab-modal-header {
      border-bottom: none;
      padding-bottom: 4px;
    }

    .ab-modal-footer {
      border-top: none;
      padding-top: 4px;
    }
  }
}

.ab-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--color-border);
}

.ab-modal-title {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
  color: var(--color-text);
}

.ab-modal-body {
  flex: 1;
  padding: 16px 18px;
  overflow-y: auto;
  font-size: 14px;
  color: var(--color-text);
}

.ab-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid var(--color-border);
}
</style>
