<script lang="ts" setup>
// 列表上方的操作行：搜索 / 筛选 / 动作三个插槽，一处定义响应式换行。
withDefaults(
  defineProps<{
    /** 吸顶（长列表页） */
    sticky?: boolean;
  }>(),
  {
    sticky: false,
  }
);
</script>

<template>
  <div class="ab-toolbar" :class="{ 'ab-toolbar--sticky': sticky }">
    <div v-if="$slots.search" class="ab-toolbar-search">
      <slot name="search"></slot>
    </div>
    <div v-if="$slots.filters" class="ab-toolbar-filters">
      <slot name="filters"></slot>
    </div>
    <div v-if="$slots.actions" class="ab-toolbar-actions">
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ab-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  width: 100%;

  &--sticky {
    position: sticky;
    top: 0;
    z-index: var(--z-sticky);
    background: color-mix(in srgb, var(--color-bg) 92%, transparent);
    backdrop-filter: blur(6px);
    padding: 8px 0;
  }
}

.ab-toolbar-search {
  flex: 1;
  min-width: 180px;
}

.ab-toolbar-filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.ab-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
</style>
