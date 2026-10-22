<script lang="ts" setup>
// Soft Ink 通用按钮：页面中唯一的按钮词汇（禁止裸 <button> / NButton）。
// danger 变体默认为柔和填充，hover 时升级为实色（Primer 式渐进破坏确认）。
const {
  variant = 'secondary',
  size = 'md',
  type = 'button',
  loading = false,
  disabled = false,
  block = false,
} = defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md';
  type?: 'button' | 'submit';
  loading?: boolean;
  disabled?: boolean;
  block?: boolean;
}>();

const emit = defineEmits<{ click: [event: MouseEvent] }>();

function onClick(event: MouseEvent) {
  if (disabled || loading) return;
  emit('click', event);
}
</script>

<template>
  <button
    class="ab-btn"
    :class="[
      `ab-btn--${variant}`,
      `ab-btn--${size}`,
      block && 'ab-btn--block',
      loading && 'ab-btn--loading',
    ]"
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    @click="onClick"
  >
    <!-- loading 时文字只隐藏不移除，转圈叠在原位，按钮尺寸不变 -->
    <span class="ab-btn-label">
      <slot name="icon" />
      <slot />
    </span>
    <span v-if="loading" class="ab-btn-spin" aria-hidden="true" />
  </button>
</template>

<style lang="scss" scoped>
.ab-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color var(--transition-fast),
    border-color var(--transition-fast), color var(--transition-fast);

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  &--md {
    height: 34px;
    padding: 0 14px;
    font-size: 14px;

    @include forTouch {
      height: var(--touch-target);
    }
  }

  &--sm {
    height: 28px;
    padding: 0 10px;
    font-size: 13px;

    // 触屏统一保证 44px 命中区（PRODUCT.md 无障碍约定）
    @include forTouch {
      height: var(--touch-target);
    }
  }

  &--block {
    width: 100%;
  }

  &--primary {
    background: var(--color-primary);
    color: var(--color-white);

    &:hover:not(:disabled) {
      background: var(--color-primary-hover);
    }
  }

  &--secondary {
    background: var(--color-surface-2);
    color: var(--color-text);

    &:hover:not(:disabled) {
      background: var(--color-surface-hover);
    }
  }

  &--ghost {
    background: transparent;
    color: var(--color-text);

    &:hover:not(:disabled) {
      background: var(--color-surface-2);
    }
  }

  &--danger {
    background: var(--color-surface-2);
    color: var(--color-danger);

    &:hover:not(:disabled) {
      background: var(--color-danger);
      color: var(--color-white);
    }

    &:focus-visible {
      outline-color: var(--color-danger);
    }
  }
}

// 调用方写在按钮上的 gap / justify-content 透传给插槽内容；min-width:0 让内容可收缩、省略
.ab-btn-label {
  display: inline-flex;
  align-items: center;
  gap: inherit;
  justify-content: inherit;
  min-width: 0;
  max-width: 100%;

  // 用 opacity 而非 visibility：保留按钮的可访问名称
  .ab-btn--loading & {
    opacity: 0;
  }
}

.ab-btn-spin {
  position: absolute;
  inset: 0;
  margin: auto;
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  border-radius: 50%;
  border: 2px solid color-mix(in srgb, currentColor 35%, transparent);
  border-top-color: currentColor;
  animation: ab-btn-rotate 0.7s linear infinite;

  @media (prefers-reduced-motion: reduce) {
    animation-duration: 1.6s;
  }
}

@keyframes ab-btn-rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>
