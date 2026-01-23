<script lang="ts" setup>
import { NSpin } from 'naive-ui';

const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'warn';
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

defineEmits(['click']);

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
      <slot></slot>
    </NSpin>
  </Component>
</template>

<style lang="scss" scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  outline: none;
  color: #fff;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  transition: background-color var(--transition-fast),
              transform var(--transition-fast),
              box-shadow var(--transition-fast);

  &:active {
    transform: scale(0.97);
  }

  // Sizes
  &--big {
    border-radius: var(--radius-md);
    font-size: 18px;
    width: 276px;
    height: 55px;
  }

  &--normal {
    border-radius: var(--radius-sm);
    font-size: 14px;
    width: 170px;
    height: 36px;
  }

  &--small {
    border-radius: var(--radius-sm);
    font-size: 12px;
    width: 86px;
    height: 28px;
  }

  // Types
  &--primary {
    background: var(--color-primary);

    &:hover {
      background: var(--color-primary-hover);
      box-shadow: 0 2px 8px color-mix(in srgb, var(--color-primary) 30%, transparent);
    }
  }

  &--warn {
    background: var(--color-danger);

    &:hover {
      filter: brightness(0.9);
      box-shadow: 0 2px 8px color-mix(in srgb, var(--color-danger) 30%, transparent);
    }
  }
}
</style>
