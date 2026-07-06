<script lang="ts" setup>
// Soft Ink 状态标记：方形色块 + 墨色文字。页面上唯一的语义色载体，
// 回答“是否在正常工作”。四种状态取代旧的 running 布尔值。
const props = withDefaults(
  defineProps<{
    state: 'running' | 'stopped' | 'paused' | 'degraded';
    /** 状态文字（省略则只渲染色块，需自带 aria 上下文） */
    label?: string;
    /** 次要说明，如 “next poll 3 min” */
    detail?: string;
    size?: 'sm' | 'md';
  }>(),
  {
    label: '',
    detail: '',
    size: 'md',
  }
);

const ariaText = computed(() => props.label || props.state);
</script>

<template>
  <span
    class="ab-status"
    :class="[`ab-status--${state}`, `ab-status--${size}`]"
    role="status"
    :aria-label="detail ? `${ariaText} — ${detail}` : ariaText"
  >
    <!-- 状态灯：外圈细线，内里是灯 -->
    <span class="ab-status-ring" aria-hidden="true">
      <span class="ab-status-mark"></span>
    </span>
    <span v-if="label" class="ab-status-label">{{ label }}</span>
    <span v-if="detail" class="ab-status-detail">{{ detail }}</span>
  </span>
</template>

<style lang="scss" scoped>
.ab-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);

  &--sm {
    font-size: 12px;
    gap: 6px;
  }
}

.ab-status-ring {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  border: 2px solid var(--color-border);
  border-radius: 50%;
  transition: border-color var(--transition-normal);

  .ab-status--sm & {
    width: 14px;
    height: 14px;
    border-width: 1.5px;
  }
}

.ab-status-mark {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background-color var(--transition-fast);

  .ab-status--sm & {
    width: 6px;
    height: 6px;
  }

  .ab-status--running & {
    background: var(--color-success);
    animation: ab-status-pulse 2s ease-in-out infinite;
  }

  .ab-status--stopped & {
    background: var(--color-danger);
  }

  .ab-status--paused & {
    background: var(--color-text-muted);
  }

  .ab-status--degraded & {
    background: var(--color-warning);
  }
}

.ab-status-label {
  color: var(--color-text);
}

.ab-status-detail {
  color: var(--color-text-secondary);
  font-weight: 400;
  font-family: var(--font-mono);
  font-size: 0.92em;
  font-variant-numeric: tabular-nums;
}

@keyframes ab-status-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ab-status-mark {
    animation: none !important;
  }
}
</style>
