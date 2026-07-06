<script lang="ts" setup>
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
    maxHeight?: string;
  }>(),
  {
    title: '',
    size: 'md',
    closable: true,
    maxHeight: '85dvh',
  }
);

const emit = defineEmits<{ close: [] }>();

const show = defineModel<boolean>('show', { default: false });

const { isMobile } = useBreakpointQuery();

function close() {
  if (!props.closable) return;
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
    :max-height="maxHeight"
    @update:show="show = $event"
    @close="emit('close')"
  >
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </AbBottomSheet>

  <!-- 桌面/平板：居中对话框 -->
  <TransitionRoot v-else appear :show="show" as="template">
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
            :class="`ab-modal-panel--${size}`"
          >
            <header v-if="title || closable" class="ab-modal-header">
              <DialogTitle as="h2" class="ab-modal-title">
                {{ title }}
              </DialogTitle>
              <AbIconButton
                v-if="closable"
                class="ab-modal-close"
                size="sm"
                :label="$t('common.cancel')"
                @click="close"
              >
                <Close theme="outline" size="16" />
              </AbIconButton>
            </header>

            <div class="ab-modal-body" :style="{ maxHeight }">
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
