<script lang="ts" setup>
// 细进度条（下载页）：轨道用 surface-2，进行中为主色，错误为 danger。
const props = withDefaults(
  defineProps<{
    /** 0–100 */
    value: number;
    label?: string;
    state?: 'active' | 'error';
  }>(),
  {
    value: 0,
    label: '',
    state: 'active',
  }
);

const clamped = computed(() => Math.min(100, Math.max(0, props.value)));
</script>

<template>
  <div class="ab-progress">
    <div
      class="ab-progress-track"
      role="progressbar"
      :aria-valuenow="Math.round(clamped)"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="label || undefined"
    >
      <div
        class="ab-progress-fill"
        :class="`ab-progress-fill--${state}`"
        :style="{ transform: `scaleX(${clamped / 100})` }"
      ></div>
    </div>
    <span v-if="label" class="ab-progress-label">{{ label }}</span>
  </div>
</template>

<style lang="scss" scoped>
.ab-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.ab-progress-track {
  flex: 1;
  height: 5px;
  border-radius: var(--radius-full);
  background: var(--color-surface-2);
  overflow: hidden;
}

.ab-progress-fill {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-full);
  transform-origin: left center;
  transition: transform var(--transition-normal);

  &--active {
    background: var(--color-primary);
  }

  &--error {
    background: var(--color-danger);
  }
}

.ab-progress-label {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
</style>
