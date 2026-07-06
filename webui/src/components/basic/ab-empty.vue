<script lang="ts" setup>
// Soft Ink 空状态：左对齐的说明文字 + 一个下一步动作 —
// 教用户界面怎么用，而不是居中图标块 + “暂无数据”。
withDefaults(
  defineProps<{
    title: string;
    description?: string;
  }>(),
  {
    description: '',
  }
);
</script>

<template>
  <div class="ab-empty">
    <p class="ab-empty-title">{{ title }}</p>
    <p v-if="description" class="ab-empty-description">{{ description }}</p>
    <div v-if="$slots.action" class="ab-empty-action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ab-empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 18px;
  border: 1px dashed var(--color-border-hover);
  border-radius: var(--radius-md);
}

.ab-empty-title {
  margin: 0;
  font-size: 14.5px;
  font-weight: 600;
  color: var(--color-text);
}

.ab-empty-description {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  max-width: 52ch;
}

.ab-empty-action {
  margin-top: 6px;
}
</style>
