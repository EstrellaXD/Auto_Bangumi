<script lang="ts" setup>
import {
  computed,
  onWatcherCleanup,
  ref,
  useId,
  useTemplateRef,
  watch,
} from 'vue';
import { usePointerSwipe } from '@vueuse/core';
import { X } from '@lucide/vue';
import { NDrawer } from 'naive-ui';
import AbIconButton from './ab-icon-button.vue';

// 底部抽屉：naive-ui NDrawer 提供焦点陷阱、Esc/遮罩关闭与 role="dialog"；
// NDrawer 本身只当透明外壳，可见面板与拖拽/键盘位移都在内层 div 上。
const {
  title,
  closeable = true,
  showClose = true,
  closeLabel = 'Close',
  maxHeight = '85dvh',
  fullscreen = false,
  avoidKeyboard = true,
} = defineProps<{
  title?: string;
  closeable?: boolean;
  showClose?: boolean;
  closeLabel?: string;
  maxHeight?: string;
  fullscreen?: boolean;
  avoidKeyboard?: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const show = defineModel<boolean>('show', { required: true });

const titleId = useId();
const dragHandleRef = useTemplateRef<HTMLElement>('dragHandle');
const panelRef = useTemplateRef<HTMLElement>('panel');
const translateY = ref(0);
const isDragging = ref(false);
const keyboardHeight = ref(0);
const panelMaxHeight = computed(() => (fullscreen ? '100dvh' : maxHeight));

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
  () => [show.value, avoidKeyboard] as const,
  ([isVisible, shouldAvoidKeyboard]) => {
    const viewport = window.visualViewport;
    if (!isVisible || !shouldAvoidKeyboard || !viewport) return;
    viewport.addEventListener('resize', handleViewportResize);
    viewport.addEventListener('scroll', handleViewportResize);
    handleViewportResize();
    // 下次触发或卸载时撤掉监听
    onWatcherCleanup(() => {
      viewport.removeEventListener('resize', handleViewportResize);
      viewport.removeEventListener('scroll', handleViewportResize);
      keyboardHeight.value = 0;
    });
  },
  { immediate: true }
);

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
  if (closeable) {
    show.value = false;
    emit('close');
  }
}
</script>

<template>
  <NDrawer
    :show="show"
    placement="bottom"
    height="auto"
    class="ab-bottom-sheet"
    :mask-closable="closeable"
    :close-on-esc="closeable"
    :aria-labelledby="title ? titleId : undefined"
    :auto-focus="false"
    @after-enter="panelRef?.focus({ preventScroll: true })"
    @update:show="(value: boolean) => value || close()"
  >
    <!-- 焦点给面板本身（与 headlessui 一致不聚焦输入框）：NDrawer 默认聚焦
         第一个输入框，手机上一打开就会弹出键盘 -->
    <div
      ref="panel"
      tabindex="-1"
      data-testid="bottom-sheet-panel"
      class="ab-bottom-sheet__panel"
      :class="{ 'ab-bottom-sheet__panel--fullscreen': fullscreen }"
      :style="[sheetStyle, { maxHeight: panelMaxHeight }]"
    >
      <!-- Drag handle -->
      <div ref="dragHandle" class="ab-bottom-sheet__handle">
        <div class="ab-bottom-sheet__handle-bar" />
      </div>

      <!-- Title -->
      <div
        v-if="title || (closeable && showClose)"
        class="ab-bottom-sheet__header"
      >
        <h3 v-if="title" :id="titleId" class="ab-bottom-sheet__title">
          {{ title }}
        </h3>
        <AbIconButton
          v-if="closeable && showClose"
          class="ab-bottom-sheet__close"
          size="md"
          :label="closeLabel"
          @click="close"
        >
          <X :size="16" />
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
    </div>
  </NDrawer>
</template>

<style lang="scss" scoped>
.ab-bottom-sheet {
  &__panel {
    position: relative;
    width: 100%;
    max-width: 640px;
    margin: 0 auto;
    max-height: 85dvh; // Use dynamic viewport height for iOS Safari keyboard support
    background: var(--color-surface);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    box-shadow: var(--shadow-lg);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    pointer-events: auto;
    outline: none;
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

<!-- 不加 scoped：NDrawer 把 class 合并到传送到 body 的 .n-drawer 上，
     scoped 选择器命中不了。外壳透明且不接收点击，两侧点击落到遮罩上。 -->
<style lang="scss">
.ab-bottom-sheet.n-drawer {
  background: none;
  box-shadow: none;
  pointer-events: none;
}

// 自定义 ::-webkit-scrollbar 让 WebKit 用常规滚动条，固定容器的包含块会扣掉
// 滚动条宽度（html 已 overflow: hidden 也一样），全屏面板（100dvh）就被顶出视口。
// 容器按视口尺寸铺满，与面板一致
.n-drawer-container:has(.ab-bottom-sheet) {
  width: 100vw;
  height: 100vh;
  height: 100dvh;
}

.n-drawer-container:has(.ab-bottom-sheet) > .n-drawer-mask {
  backdrop-filter: blur(4px);
}
</style>
