<script lang="ts" setup>
// 图标按钮：label 必填（即 aria-label）；触屏下命中区 ≥ 44px。
const props = withDefaults(
  defineProps<{
    /** 无文本按钮的可访问名称（必填） */
    label: string;
    size?: 'sm' | 'md';
    /** solid：主色填充（用于卡片上的主要动作）；round：圆形 */
    variant?: 'ghost' | 'solid';
    round?: boolean;
    disabled?: boolean;
  }>(),
  {
    size: 'md',
    variant: 'ghost',
    round: false,
    disabled: false,
  }
);

const emit = defineEmits<{ click: [event: MouseEvent] }>();

function onClick(event: MouseEvent) {
  if (props.disabled) return;
  emit('click', event);
}
</script>

<template>
  <button
    class="ab-icon-btn"
    :class="[
      `ab-icon-btn--${size}`,
      `ab-icon-btn--${variant}`,
      round && 'ab-icon-btn--round',
    ]"
    type="button"
    :aria-label="label"
    :title="label"
    :disabled="disabled"
    @click="onClick"
  >
    <slot></slot>
  </button>
</template>

<style lang="scss" scoped>
.ab-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color var(--transition-fast),
    color var(--transition-fast);

  &:hover:not(:disabled) {
    background: var(--color-surface-2);
    color: var(--color-text);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  &--md {
    width: 32px;
    height: 32px;
    font-size: 17px;

    @include forTouch {
      width: var(--touch-target);
      height: var(--touch-target);
    }
  }

  &--sm {
    width: 26px;
    height: 26px;
    font-size: 14px;

    @include forTouch {
      width: 36px;
      height: 36px;
    }
  }

  @media screen and (max-width: 639px) {
    &--md,
    &--sm {
      width: var(--touch-target);
      height: var(--touch-target);
    }
  }

  &--solid {
    background: var(--color-primary);
    color: var(--color-white);

    &:hover:not(:disabled) {
      background: var(--color-primary-hover);
      color: var(--color-white);
    }
  }

  &--round {
    border-radius: var(--radius-full);
  }
}
</style>
