<script lang="ts" setup>
// 细进度条（下载页）：轨道用半透明 muted 色（任何行底色上都可见），进行中为主色，错误为 danger。
const { value = 0, label = '', state = 'active' } = defineProps<{
  /** 0–100 */
  value: number;
  label?: string;
  state?: 'active' | 'error';
}>();

const clamped = computed(() => Math.min(100, Math.max(0, value)));
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
      />
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
  background: color-mix(in srgb, var(--color-text-muted) 30%, transparent);
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
  // 固定宽度放下 '100%'，各行轨道等长、数字右对齐
  min-width: 4ch;
  text-align: right;
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
</style>
