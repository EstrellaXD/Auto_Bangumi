<script lang="ts" setup>
import AbField from './basic/ab-field.vue';

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
  <AbField :label="label">
    <div class="offset-controls">
      <ab-input v-model="proxyValue" type="number" class="offset-input" />
      <slot name="action" />
    </div>
  </AbField>
</template>

<style lang="scss" scoped>
// 控件列与其它 AbField 行同宽（200px）；有操作按钮时输入框收窄让位
.offset-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;

  @include forTablet {
    width: 200px;
  }
}

// 压过 AbField 给 .ab-input 的 200px 宽度下限，让输入框给按钮让位
.offset-controls .ab-input.offset-input {
  flex: 1 1 0;
  min-width: 0;

  @include forTouch {
    height: var(--touch-target);
  }
}
</style>
