<script lang="ts" setup>
// 骨架屏（加载态用骨架，不在内容中放 spinner）。
// preset 对应真实布局：lines（文本）/ row（列表行）/ card（卡片）。
withDefaults(
  defineProps<{
    preset?: 'lines' | 'row' | 'card';
    count?: number;
  }>(),
  {
    preset: 'lines',
    count: 3,
  }
);

// 行宽做点参差，避免整齐得像占位框
const widths = ['62%', '88%', '40%', '75%', '55%'];
</script>

<template>
  <div class="ab-skeleton" aria-hidden="true">
    <template v-if="preset === 'lines'">
      <span
        v-for="i in count"
        :key="i"
        class="ab-skeleton-line"
        :style="{ width: widths[(i - 1) % widths.length] }"
      ></span>
    </template>

    <template v-else-if="preset === 'row'">
      <span v-for="i in count" :key="i" class="ab-skeleton-row">
        <span class="ab-skeleton-line" style="width: 46%"></span>
        <span
          class="ab-skeleton-line ab-skeleton-line--dim"
          style="width: 68%"
        ></span>
      </span>
    </template>

    <template v-else>
      <span v-for="i in count" :key="i" class="ab-skeleton-card"></span>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.ab-skeleton {
  display: flex;
  flex-direction: column;
  gap: 9px;
  width: 100%;
}

@mixin shimmer {
  background: linear-gradient(
    90deg,
    var(--color-surface-2) 25%,
    var(--color-surface-hover) 45%,
    var(--color-surface-2) 65%
  );
  background-size: 240% 100%;
  animation: ab-skeleton-shimmer 1.4s ease-in-out infinite;

  @media (prefers-reduced-motion: reduce) {
    animation: none;
  }
}

.ab-skeleton-line {
  height: 13px;
  border-radius: var(--radius-sm);
  @include shimmer;

  &--dim {
    height: 11px;
    opacity: 0.7;
  }
}

.ab-skeleton-row {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--color-surface-2);

  .ab-skeleton-line {
    background: linear-gradient(
      90deg,
      var(--color-surface-hover) 25%,
      var(--color-surface) 45%,
      var(--color-surface-hover) 65%
    );
    background-size: 240% 100%;
    animation: ab-skeleton-shimmer 1.4s ease-in-out infinite;

    @media (prefers-reduced-motion: reduce) {
      animation: none;
    }
  }
}

.ab-skeleton-card {
  height: 120px;
  border-radius: var(--radius-md);
  @include shimmer;
}

@keyframes ab-skeleton-shimmer {
  from {
    background-position: 120% 0;
  }
  to {
    background-position: -120% 0;
  }
}
</style>
