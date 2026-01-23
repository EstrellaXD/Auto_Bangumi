<script lang="ts" setup>
withDefaults(
  defineProps<{
    type: 'primary' | 'warn' | 'inactive' | 'active' | 'notify';
    title: string;
  }>(),
  {
    type: 'primary',
    title: 'title',
  }
);
</script>

<template>
  <span class="tag" :class="`tag--${type}`">
    {{ title }}
  </span>
</template>

<style lang="scss" scoped>
.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 10px;
  font-weight: 500;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid;
  transition: background-color var(--transition-fast),
              border-color var(--transition-fast),
              color var(--transition-fast);

  &--primary {
    background: var(--color-primary-light);
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &--warn {
    background: color-mix(in srgb, var(--color-danger) 10%, transparent);
    border-color: var(--color-danger);
    color: var(--color-danger);
  }

  &--inactive {
    background: var(--color-surface-hover);
    border-color: var(--color-border);
    color: var(--color-text-muted);
  }

  &--active {
    background: color-mix(in srgb, var(--color-success) 10%, transparent);
    border-color: var(--color-success);
    color: var(--color-success);
  }

  &--notify {
    background: color-mix(in srgb, var(--color-warning) 10%, transparent);
    border-color: var(--color-warning);
    color: var(--color-warning);
  }
}
</style>
