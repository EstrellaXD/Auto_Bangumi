<script lang="ts" setup>
import { computed, ref } from 'vue';

const props = withDefaults(
  defineProps<{
    loading?: boolean;
    threshold?: number;
    disabled?: boolean;
  }>(),
  {
    loading: false,
    threshold: 60,
    disabled: false,
  }
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const containerRef = ref<HTMLElement | null>(null);
const pullDistance = ref(0);
const isPulling = ref(false);
const startY = ref(0);

const pullStyle = computed(() => {
  if (pullDistance.value > 0) {
    return {
      transform: `translateY(${Math.min(pullDistance.value, props.threshold * 1.5)}px)`,
      transition: isPulling.value ? 'none' : 'transform var(--transition-normal)',
    };
  }
  return {
    transition: 'transform var(--transition-normal)',
  };
});

const indicatorOpacity = computed(() => {
  return Math.min(pullDistance.value / props.threshold, 1);
});

const indicatorRotation = computed(() => {
  return Math.min(pullDistance.value / props.threshold, 1) * 180;
});

const isTriggered = computed(() => pullDistance.value >= props.threshold);

function onTouchStart(e: TouchEvent) {
  if (props.disabled || props.loading) return;
  const container = containerRef.value;
  if (!container || container.scrollTop > 0) return;

  startY.value = e.touches[0].clientY;
  isPulling.value = true;
}

function onTouchMove(e: TouchEvent) {
  if (!isPulling.value || props.disabled || props.loading) return;
  const container = containerRef.value;
  if (!container || container.scrollTop > 0) {
    isPulling.value = false;
    pullDistance.value = 0;
    return;
  }

  const currentY = e.touches[0].clientY;
  const diff = currentY - startY.value;

  if (diff > 0) {
    // Apply resistance: the further you pull, the harder it gets
    pullDistance.value = diff * 0.5;
    e.preventDefault();
  }
}

function onTouchEnd() {
  if (!isPulling.value) return;
  isPulling.value = false;

  if (isTriggered.value && !props.loading) {
    emit('refresh');
  }
  pullDistance.value = 0;
}
</script>

<template>
  <div
    ref="containerRef"
    class="ab-pull-refresh"
    @touchstart.passive="onTouchStart"
    @touchmove="onTouchMove"
    @touchend="onTouchEnd"
    @touchcancel="onTouchEnd"
  >
    <!-- Pull indicator -->
    <div class="ab-pull-refresh__indicator" :style="{ opacity: indicatorOpacity }">
      <div
        v-if="loading"
        class="ab-pull-refresh__spinner"
      />
      <svg
        v-else
        class="ab-pull-refresh__arrow"
        :style="{ transform: `rotate(${indicatorRotation}deg)` }"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M12 19V5M5 12l7-7 7 7" />
      </svg>
    </div>

    <!-- Content -->
    <div class="ab-pull-refresh__content" :style="pullStyle">
      <slot />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ab-pull-refresh {
  position: relative;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  height: 100%;

  &__indicator {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 40px;
    color: var(--color-primary);
    pointer-events: none;
    z-index: 1;
  }

  &__arrow {
    transition: transform var(--transition-fast);
  }

  &__spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  &__content {
    min-height: 100%;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
