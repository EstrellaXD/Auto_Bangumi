<script lang="ts" setup>
/**
 * 单个数字 offset 行：标签 + 数字输入 + 可选的操作插槽（如“自动检测”按钮）。
 * ab-add-rss 用它承载 episode_offset + 检测按钮，ab-edit-rule 用它承载
 * season_offset / episode_offset 两个纯输入行。
 */
const props = defineProps<{
  label: string;
  modelValue: number;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void;
}>();

// v-model.number 代理：保持与原生 input[type=number] + .number 修饰符完全一致的解析行为
const proxyValue = computed({
  get: () => props.modelValue,
  set: (value: number) => emit('update:modelValue', value),
});
</script>

<template>
  <div class="advanced-row">
    <label class="advanced-label">{{ label }}</label>
    <div class="advanced-control offset-controls">
      <input
        v-model.number="proxyValue"
        type="number"
        ab-input
        class="offset-input"
      />
      <slot name="action" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.advanced-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 32px;
}

.advanced-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  line-height: 32px;
}

.advanced-control {
  display: flex;
  justify-content: flex-end;
}

.offset-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-height: 32px;
}

.offset-input {
  width: 70px;
  height: 32px;
  text-align: center;

  @include forTouch {
    width: 84px;
    height: var(--touch-target);
  }
}
</style>
