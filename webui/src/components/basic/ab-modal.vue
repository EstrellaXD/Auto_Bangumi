<script lang="ts" setup>
import { ref, watch } from 'vue';
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue';
import { Close } from '@icon-park/vue-next';
import AbBottomSheet from './ab-bottom-sheet.vue';
import AbIconButton from './ab-icon-button.vue';
import { useBreakpointQuery } from '@/hooks/useBreakpointQuery';

// 唯一的自适应弹窗组件（合并旧 ab-popup / ab-adaptive-modal）：
// 桌面居中对话框，移动端底部抽屉。headlessui Dialog 提供焦点陷阱与 aria。
const props = withDefaults(
  defineProps<{
    title?: string;
    size?: 'sm' | 'md' | 'lg';
    /** false 时禁用遮罩点击/关闭按钮（用于流程中不可中断的弹窗） */
    closable?: boolean;
    /** 隐藏右上角 X（confirm 类弹窗：Esc/遮罩仍可关闭） */
    showClose?: boolean;
    maxHeight?: string;
    /** 可选的桌面最大宽度覆盖；移动端抽屉不受影响 */
    desktopMaxWidth?: string;
    /** 移动端用整屏抽屉承载长表单 */
    mobileFullscreen?: boolean;
    /** 移动端软键盘出现时是否把抽屉整体上移 */
    avoidKeyboard?: boolean;
  }>(),
  {
    title: '',
    size: 'md',
    closable: true,
    showClose: true,
    maxHeight: '85dvh',
    mobileFullscreen: false,
    avoidKeyboard: true,
  }
);

const emit = defineEmits<{ close: []; 'after-leave': [] }>();

const show = defineModel<boolean>('show', { default: false });

const { isMobile } = useBreakpointQuery();
const mobileRenderer = ref(isMobile.value);
let closeCyclePending = false;

// Keep one renderer for the whole open/close cycle. Swapping branches while a
// leave transition is running unmounts that transition before after-leave.
watch(show, (visible, wasVisible) => {
  if (visible) {
    if (!closeCyclePending) {
      mobileRenderer.value = isMobile.value;
    }
    closeCyclePending = false;
  } else if (wasVisible) {
    closeCyclePending = true;
  }
});

function close() {
  if (!props.closable) return;
  show.value = false;
  emit('close');
}

function handleAfterLeave() {
  if (!closeCyclePending) return;

  closeCyclePending = false;
  emit('after-leave');
  mobileRenderer.value = isMobile.value;
}
</script>

<template>
  <!-- 移动端：底部抽屉 -->
  <AbBottomSheet
    v-if="mobileRenderer"
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
    @after-leave="handleAfterLeave"
  >
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </AbBottomSheet>

  <!-- 桌面/平板：居中对话框 -->
  <TransitionRoot
    v-else
    appear
    :show="show"
    as="template"
    @after-leave="handleAfterLeave"
  >
    <Dialog class="ab-modal" @close="close">
      <TransitionChild
        as="template"
        enter="duration-200 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-150 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="ab-modal-backdrop" aria-hidden="true" />
      </TransitionChild>

      <div class="ab-modal-wrapper">
        <TransitionChild
          as="template"
          enter="duration-200 ease-out"
          enter-from="opacity-0 scale-97"
          enter-to="opacity-100 scale-100"
          leave="duration-150 ease-in"
          leave-from="opacity-100 scale-100"
          leave-to="opacity-0 scale-97"
        >
          <DialogPanel
            class="ab-modal-panel"
            :class="[
              `ab-modal-panel--${size}`,
              !$slots.default && 'ab-modal-panel--bare',
            ]"
            :style="desktopMaxWidth ? { maxWidth: desktopMaxWidth } : undefined"
          >
            <header
              v-if="title || (closable && showClose)"
              class="ab-modal-header"
            >
              <DialogTitle as="h2" class="ab-modal-title">
                {{ title }}
              </DialogTitle>
              <AbIconButton
                v-if="closable && showClose"
                class="ab-modal-close"
                size="sm"
                :label="$t('common.close')"
                @click="close"
              >
                <Close theme="outline" size="16" />
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
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<style lang="scss" scoped>
.ab-modal {
  position: relative;
  z-index: var(--z-modal);
}

.ab-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal-backdrop);
  background: var(--color-overlay);
}

.ab-modal-wrapper {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  overflow-y: auto;
}

.ab-modal-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
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
