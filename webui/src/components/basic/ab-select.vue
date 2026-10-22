<script lang="ts" setup>
import { computed, inject } from 'vue';
import { NSelect } from 'naive-ui';
import type { SelectOption } from 'naive-ui';
import { abFieldInjectionKey } from './ab-field.vue';
import type { SelectItem } from '#/components';

// NSelect 的统一封装：选项归一化 + ab-field aria 接线在这里定一次。
const {
  items,
  options,
  placeholder = '',
  disabled = false,
  error = false,
} = defineProps<{
  /** 允许 string 或 {label?, value} 混合（旧 ab-setting 的格式） */
  items?: Array<SelectItem | string>;
  /** 已是 naive 格式时直接传 options */
  options?: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  ariaLabel?: string;
}>();

const model = defineModel<string | number | null>({ default: null });

const field = inject(abFieldInjectionKey, null);

const normalizedOptions = computed<SelectOption[]>(() => {
  if (options) return options;
  return (items ?? []).map((item) =>
    typeof item === 'object'
      ? { label: item.label ?? String(item.value), value: item.value }
      : { label: item, value: item }
  );
});

const invalid = computed(() => error || field?.invalid.value === true);

const menuProps = { role: 'listbox' } as const;

function optionNodeProps() {
  return { role: 'option' };
}
</script>

<template>
  <NSelect
    v-model:value="model"
    class="ab-select"
    :class="{ 'ab-select--error': invalid }"
    :options="normalizedOptions"
    :placeholder="placeholder"
    :disabled="disabled"
    role="combobox"
    aria-haspopup="listbox"
    :aria-label="ariaLabel"
    :aria-labelledby="field?.labelId"
    :aria-describedby="field?.describedBy.value"
    :menu-props="menuProps"
    :node-props="optionNodeProps"
  />
</template>

<style lang="scss" scoped>
.ab-select {
  max-width: 100%;

  // 触屏与 ab-input、ab-button 同为 44px 命中区（naive 把 --n-height 写在行内样式上）
  @include forTouch {
    :deep(.n-base-selection) {
      --n-height: var(--touch-target) !important;
    }
  }

  &--error {
    :deep(.n-base-selection) {
      --n-border: 1px solid var(--color-danger) !important;
    }
  }
}
</style>
