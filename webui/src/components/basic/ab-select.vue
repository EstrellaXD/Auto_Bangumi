<script lang="ts" setup>
import { computed, inject } from 'vue';
import { NSelect } from 'naive-ui';
import { isObject } from 'radash';
import type { SelectOption } from 'naive-ui';
import { abFieldInjectionKey } from './ab-field.vue';
import type { SelectItem } from '#/components';

// NSelect 的统一封装：选项归一化 + ab-field aria 接线在这里定一次。
const props = withDefaults(
  defineProps<{
    /** 允许 string 或 {label?, value} 混合（旧 ab-setting 的格式） */
    items?: Array<SelectItem | string>;
    /** 已是 naive 格式时直接传 options */
    options?: SelectOption[];
    placeholder?: string;
    disabled?: boolean;
    error?: boolean;
    ariaLabel?: string;
  }>(),
  {
    items: undefined,
    options: undefined,
    placeholder: '',
    disabled: false,
    error: false,
    ariaLabel: undefined,
  }
);

const model = defineModel<string | number | null>({ default: null });

const field = inject(abFieldInjectionKey, null);

const normalizedOptions = computed<SelectOption[]>(() => {
  if (props.options) return props.options;
  return (props.items ?? []).map((item) =>
    isObject(item)
      ? { label: item.label ?? String(item.value), value: item.value }
      : { label: item, value: item }
  );
});

const invalid = computed(() => props.error || field?.invalid.value === true);
</script>

<template>
  <NSelect
    v-model:value="model"
    class="ab-select"
    :class="{ 'ab-select--error': invalid }"
    :options="normalizedOptions"
    :placeholder="placeholder"
    :disabled="disabled"
    :aria-label="ariaLabel"
    :aria-labelledby="field?.labelId"
    :aria-describedby="field?.describedBy.value"
  ></NSelect>
</template>

<style lang="scss" scoped>
.ab-select {
  max-width: 100%;

  &--error {
    :deep(.n-base-selection) {
      --n-border: 1px solid var(--color-danger) !important;
    }
  }
}
</style>
