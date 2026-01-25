<script lang="ts" setup>
import { NSpin } from 'naive-ui';

const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'secondary' | 'warn';
    size?: 'big' | 'normal' | 'small';
    link?: string | null;
    loading?: boolean;
  }>(),
  {
    type: 'primary',
    size: 'normal',
    link: null,
    loading: false,
  }
);

defineEmits<{ click: [] }>();

const buttonSize = computed(() => {
  switch (props.size) {
    case 'big':
      return 'btn--big';
    case 'normal':
      return 'btn--normal';
    case 'small':
      return 'btn--small';
  }
});
</script>

<template>
  <Component
    :is="link !== null ? 'a' : 'button'"
    :href="link"
    class="btn"
    :class="[`btn--${type}`, buttonSize]"
    @click="$emit('click')"
  >
    <NSpin :show="loading" :size="size === 'big' ? 'large' : 'small'">
      <span class="btn-content">
        <slot></slot>
      </span>
    </NSpin>
  </Component>
</template>

<style lang="scss" scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  color: var(--color-white);
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  text-decoration: none;
  transition: background-color var(--transition-fast),
              transform var(--transition-fast),
              box-shadow var(--transition-fast);

  // Focus ring for keyboard navigation
  &:focus {
    outline: none;
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  &:active:not(:disabled) {
    transform: scale(0.97);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  // Sizes
  &--big {
    border-radius: var(--radius-md);
    font-size: 16px;
    width: 100%;
    max-width: 276px;
    height: 44px;
  }

  &--normal {
    border-radius: var(--radius-sm);
    font-size: 14px;
    width: 100%;
    max-width: 170px;
    height: 36px;
  }

  &--small {
    border-radius: var(--radius-sm);
    font-size: 13px;
    min-width: 80px;
    height: 32px;
    padding: 0 14px;
    gap: 6px;
    white-space: nowrap;
  }

  // Types
  &--primary {
    background: var(--color-primary);

    &:hover:not(:disabled) {
      background: var(--color-primary-hover);
      box-shadow: 0 2px 8px color-mix(in srgb, var(--color-primary) 30%, transparent);
    }

    &:focus-visible {
      outline-color: var(--color-primary-hover);
    }
  }

  &-content {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  &--secondary {
    background: var(--color-surface);
    color: var(--color-primary);
    border: 1px solid var(--color-border);

    &:hover:not(:disabled) {
      background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface));
      border-color: var(--color-primary);
    }

    &:focus-visible {
      outline-color: var(--color-primary);
    }
  }

  &--warn {
    background: var(--color-danger);

    &:hover:not(:disabled) {
      filter: brightness(0.9);
      box-shadow: 0 2px 8px color-mix(in srgb, var(--color-danger) 30%, transparent);
    }

    &:focus-visible {
      outline-color: var(--color-danger);
    }
  }
}
</style>
