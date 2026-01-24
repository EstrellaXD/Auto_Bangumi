<script lang="ts" setup>
import { ref, watch, computed } from 'vue';
import { usePointerSwipe } from '@vueuse/core';
import {
  TransitionRoot,
  TransitionChild,
  Dialog,
  DialogPanel,
} from '@headlessui/vue';

const props = withDefaults(
  defineProps<{
    show: boolean;
    title?: string;
    closeable?: boolean;
    maxHeight?: string;
  }>(),
  {
    closeable: true,
    maxHeight: '85vh',
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

const sheetStyle = computed(() => {
  if (isDragging.value && translateY.value > 0) {
    return {
      transform: `translateY(${translateY.value}px)`,
      transition: 'none',
    };
  }
  return {};
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
    <Dialog @close="close" class="ab-bottom-sheet">
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
            class="ab-bottom-sheet__panel"
            :style="[sheetStyle, { maxHeight }]"
          >
            <!-- Drag handle -->
            <div ref="dragHandleRef" class="ab-bottom-sheet__handle">
              <div class="ab-bottom-sheet__handle-bar" />
            </div>

            <!-- Title -->
            <div v-if="title" class="ab-bottom-sheet__header">
              <h3 class="ab-bottom-sheet__title">{{ title }}</h3>
            </div>

            <!-- Content -->
            <div class="ab-bottom-sheet__content">
              <slot />
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
  z-index: 100;
  display: flex;
  align-items: flex-end;

  &__backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
  }

  &__container {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    pointer-events: none;
  }

  &__panel {
    position: relative;
    width: 100%;
    max-width: 640px;
    background: var(--color-surface);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    box-shadow: var(--shadow-lg);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    pointer-events: auto;
    @include safeAreaBottom(padding-bottom);
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
    padding: 0 20px 12px;
    border-bottom: 1px solid var(--color-border);
  }

  &__title {
    font-size: 18px;
    font-weight: 600;
    color: var(--color-text);
    margin: 0;
  }

  &__content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    -webkit-overflow-scrolling: touch;
  }
}
</style>
