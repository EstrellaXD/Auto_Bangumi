import { computed } from 'vue';

export function useSafeArea() {
  const safeAreaTop = computed(() => 'env(safe-area-inset-top, 0px)');
  const safeAreaBottom = computed(() => 'env(safe-area-inset-bottom, 0px)');
  const safeAreaLeft = computed(() => 'env(safe-area-inset-left, 0px)');
  const safeAreaRight = computed(() => 'env(safe-area-inset-right, 0px)');

  return {
    safeAreaTop,
    safeAreaBottom,
    safeAreaLeft,
    safeAreaRight,
  };
}
