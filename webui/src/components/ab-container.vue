<script lang="ts" setup>
withDefaults(
  defineProps<{
    title: string;
  }>(),
  {
    title: 'title',
  }
);
</script>

<template>
  <div class="container-card">
    <div class="container-header">
      <div class="container-title">{{ title }}</div>
      <slot name="title-right"></slot>
    </div>

    <div class="container-body">
      <slot></slot>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.container-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: border-color var(--transition-normal);
}

.container-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  height: 34px;
  background: transparent;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  user-select: none;
  transition: color var(--transition-normal),
              border-color var(--transition-normal);
}

.container-title {
  font-size: 15px;
  font-weight: 600;
}

.container-body {
  padding: 12px 14px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 14px;
  transition: background-color var(--transition-normal),
              color var(--transition-normal);
}
</style>
