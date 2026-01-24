<script lang="ts" setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue?: number;
    showDots?: boolean;
    itemCount?: number;
  }>(),
  {
    modelValue: 0,
    showDots: true,
    itemCount: 0,
  }
);

const emit = defineEmits<{
  (e: 'update:modelValue', index: number): void;
  (e: 'change', index: number): void;
}>();

const containerRef = ref<HTMLElement | null>(null);
const currentIndex = ref(props.modelValue);

watch(
  () => props.modelValue,
  (val) => {
    currentIndex.value = val;
    scrollToIndex(val);
  }
);

function scrollToIndex(index: number) {
  const container = containerRef.value;
  if (!container) return;
  const children = container.children;
  if (children[index]) {
    (children[index] as HTMLElement).scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'start',
    });
  }
}

function onScroll() {
  const container = containerRef.value;
  if (!container) return;

  const scrollLeft = container.scrollLeft;
  const itemWidth = container.clientWidth;
  const newIndex = Math.round(scrollLeft / itemWidth);

  if (newIndex !== currentIndex.value) {
    currentIndex.value = newIndex;
    emit('update:modelValue', newIndex);
    emit('change', newIndex);
  }
}

function goTo(index: number) {
  currentIndex.value = index;
  emit('update:modelValue', index);
  emit('change', index);
  scrollToIndex(index);
}

onMounted(() => {
  if (props.modelValue > 0) {
    nextTick(() => scrollToIndex(props.modelValue));
  }
});

defineExpose({ goTo });
</script>

<template>
  <div class="ab-swipe-container">
    <div
      ref="containerRef"
      class="ab-swipe-container__track"
      @scroll.passive="onScroll"
    >
      <slot />
    </div>

    <!-- Pagination dots -->
    <div v-if="showDots && itemCount > 1" class="ab-swipe-container__dots">
      <button
        v-for="i in itemCount"
        :key="i"
        class="ab-swipe-container__dot"
        :class="{ 'ab-swipe-container__dot--active': currentIndex === i - 1 }"
        @click="goTo(i - 1)"
        :aria-label="`Go to slide ${i}`"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ab-swipe-container {
  position: relative;
  width: 100%;

  &__track {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;

    // Hide scrollbar
    scrollbar-width: none;
    &::-webkit-scrollbar {
      display: none;
    }

    > * {
      flex-shrink: 0;
      width: 100%;
      scroll-snap-align: start;
    }
  }

  &__dots {
    display: flex;
    justify-content: center;
    gap: 6px;
    padding: 12px 0;
  }

  &__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: none;
    background: var(--color-border);
    cursor: pointer;
    padding: 0;
    transition: background var(--transition-fast), transform var(--transition-fast);

    &--active {
      background: var(--color-primary);
      transform: scale(1.25);
    }
  }
}
</style>
