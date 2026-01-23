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
  overflow: hidden;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-normal),
              box-shadow var(--transition-normal);
}

.container-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 42px;
  background: var(--color-primary);
  color: #fff;
  user-select: none;

  @include forPC {
    height: 48px;
  }
}

.container-title {
  font-size: 16px;
  font-weight: 500;

  @include forPC {
    font-size: 18px;
  }
}

.container-body {
  padding: 14px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 14px;
  transition: background-color var(--transition-normal),
              color var(--transition-normal);

  @include forPC {
    padding: 20px;
  }
}
</style>
