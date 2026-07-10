<script lang="ts" setup>
import { computed, onUnmounted, ref, watch } from 'vue';
import { usePointerSwipe } from '@vueuse/core';
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue';
import { Close } from '@icon-park/vue-next';
import AbIconButton from './ab-icon-button.vue';

const props = withDefaults(
  defineProps<{
    show: boolean;
    title?: string;
    closeable?: boolean;
    showClose?: boolean;
    closeLabel?: string;
    maxHeight?: string;
    fullscreen?: boolean;
    avoidKeyboard?: boolean;
  }>(),
  {
    closeable: true,
    showClose: true,
    closeLabel: 'Close',
    maxHeight: '85dvh',
    fullscreen: false,
    avoidKeyboard: true,
  }
);

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
  (e: 'close'): void;
}>();

const sheetRef = ref<HTMLElement | null>(null);
const dragHandleRef = ref<HTMLElement | null>(null);
const translateY = ref(0);
const isDragging = ref(false);
const keyboardHeight = ref(0);
const panelMaxHeight = computed(() =>
  props.fullscreen ? '100dvh' : props.maxHeight
);

// Handle iOS Safari virtual keyboard using visualViewport API
function handleViewportResize() {
  if (window.visualViewport) {
    const viewport = window.visualViewport;
    // Calculate keyboard height as the difference between window height and viewport height
    const newKeyboardHeight = window.innerHeight - viewport.height;
    keyboardHeight.value = Math.max(0, newKeyboardHeight);
  }
}

// Set up visualViewport listeners when sheet is shown
watch(
  () => [props.show, props.avoidKeyboard] as const,
  ([isVisible, shouldAvoidKeyboard]) => {
    if (isVisible && shouldAvoidKeyboard && window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleViewportResize);
      window.visualViewport.addEventListener('scroll', handleViewportResize);
      handleViewportResize();
    } else if (window.visualViewport) {
      window.visualViewport.removeEventListener('resize', handleViewportResize);
      window.visualViewport.removeEventListener('scroll', handleViewportResize);
      keyboardHeight.value = 0;
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (window.visualViewport) {
    window.visualViewport.removeEventListener('resize', handleViewportResize);
    window.visualViewport.removeEventListener('scroll', handleViewportResize);
  }
});

const sheetStyle = computed(() => {
  const style: Record<string, string> = {};

  // Apply keyboard offset for iOS Safari
  if (keyboardHeight.value > 0) {
    style.transform = `translateY(-${keyboardHeight.value}px)`;
    style.transition = 'transform 0.25s ease-out';
  }

  // Apply drag offset
  if (isDragging.value && translateY.value > 0) {
    style.transform = `translateY(${translateY.value}px)`;
    style.transition = 'none';
  }

  return style;
});

const { distanceY } = usePointerSwipe(dragHandleRef, {
  threshold: 10,
  onSwipe() {
    if (distanceY.value < 0) {
      // Swiping down (distanceY is negative when going down in usePointerSwipe)
      translateY.value = Math.abs(distanceY.value);
      isDragging.value = true;
    }
  },
  onSwipeEnd() {
    isDragging.value = false;
    if (translateY.value > 100) {
      close();
    }
    translateY.value = 0;
  },
});

function close() {
  if (props.closeable) {
    emit('update:show', false);
    emit('close');
  }
}
</script>

<template>
  <TransitionRoot :show="show" as="template">
    <Dialog class="ab-bottom-sheet" @close="close">
      <!-- Backdrop -->
      <TransitionChild
        enter="overlay-enter-active"
        enter-from="overlay-enter-from"
        leave="overlay-leave-active"
        leave-to="overlay-leave-to"
      >
        <div class="ab-bottom-sheet__backdrop" aria-hidden="true" />
      </TransitionChild>

      <!-- Sheet panel -->
      <TransitionChild
        enter="sheet-enter-active"
        enter-from="sheet-enter-from"
        leave="sheet-leave-active"
        leave-to="sheet-leave-to"
      >
        <div class="ab-bottom-sheet__container">
          <DialogPanel
            ref="sheetRef"
            data-testid="bottom-sheet-panel"
            class="ab-bottom-sheet__panel"
            :class="{ 'ab-bottom-sheet__panel--fullscreen': fullscreen }"
            :style="[sheetStyle, { maxHeight: panelMaxHeight }]"
          >
            <!-- Drag handle -->
            <div ref="dragHandleRef" class="ab-bottom-sheet__handle">
              <div class="ab-bottom-sheet__handle-bar" />
            </div>

            <!-- Title -->
            <div
              v-if="title || (closeable && showClose)"
              class="ab-bottom-sheet__header"
            >
              <DialogTitle v-if="title" as="h3" class="ab-bottom-sheet__title">
                {{ title }}
              </DialogTitle>
              <AbIconButton
                v-if="closeable && showClose"
                class="ab-bottom-sheet__close"
                size="md"
                :label="closeLabel"
                @click="close"
              >
                <Close theme="outline" size="16" />
              </AbIconButton>
            </div>

            <!-- Content -->
            <div class="ab-bottom-sheet__content">
              <slot />
            </div>

            <!-- Footer actions -->
            <div v-if="$slots.footer" class="ab-bottom-sheet__footer">
              <slot name="footer" />
            </div>
          </DialogPanel>
        </div>
      </TransitionChild>
    </Dialog>
  </TransitionRoot>
</template>

<style lang="scss" scoped>
.ab-bottom-sheet {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: flex-end;

  &__backdrop {
    position: fixed;
    inset: 0;
    z-index: var(--z-modal-backdrop);
    background: var(--color-overlay);
    backdrop-filter: blur(4px);
  }

  &__container {
    position: fixed;
    inset: 0;
    z-index: var(--z-modal);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    pointer-events: none;
  }

  &__panel {
    position: relative;
    width: 100%;
    max-width: 640px;
    max-height: 85dvh; // Use dynamic viewport height for iOS Safari keyboard support
    background: var(--color-surface);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    box-shadow: var(--shadow-lg);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    pointer-events: auto;
    @include safeAreaBottom(padding-bottom);

    // Fallback for browsers that don't support dvh
    @supports not (max-height: 1dvh) {
      max-height: 85vh;
    }

    &--fullscreen {
      height: 100dvh;
      max-height: 100dvh;
      border-radius: 0;
      @include safeAreaTop(padding-top);

      @supports not (height: 1dvh) {
        height: 100vh;
        max-height: 100vh;
      }
    }
  }

  &__handle {
    display: flex;
    justify-content: center;
    padding: 12px 0 8px;
    cursor: grab;
    touch-action: none;

    &:active {
      cursor: grabbing;
    }
  }

  &__handle-bar {
    width: 36px;
    height: 4px;
    border-radius: var(--radius-full);
    background: var(--color-border);
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 0 20px 12px;
    border-bottom: 1px solid var(--color-border);
  }

  &__title {
    font-size: 18px;
    font-weight: 600;
    color: var(--color-text);
    margin: 0;
  }

  &__close {
    margin-left: auto;
  }

  &__content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    -webkit-overflow-scrolling: touch;

    // Ensure inputs scroll into view when focused on iOS Safari
    :deep(input),
    :deep(textarea),
    :deep(select) {
      scroll-margin-bottom: 20px;
    }
  }

  &__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 20px;
    border-top: 1px solid var(--color-border);
  }
}
</style>
