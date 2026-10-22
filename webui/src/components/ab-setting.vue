<script lang="ts" setup>
import AbField from './basic/ab-field.vue';
import AbInput from './basic/ab-input.vue';
import AbSelect from './basic/ab-select.vue';
import AbSwitch from './basic/ab-switch.vue';
import AbTagsInput from './basic/ab-tags-input.vue';
import type { AbSettingProps, SelectItem } from '#/components';

// 设置行：ab-field（标签/说明/错误/aria）+ 对应控件的组合。
const {
  css = '',
  bottomLine = false,
  description = '',
  error = '',
  required = false,
  label,
} = defineProps<AbSettingProps>();

const data = defineModel<any>('data');

const labelText = computed(() =>
  typeof label === 'function' ? label() : label
);

// 旧组件允许 v-model 绑定对象（SelectItem）；读取时取 .value，
// 写回时保持字符串（配置值均为字符串）
const selectValue = computed<string | number | null>({
  get() {
    return typeof data.value === 'object' && data.value !== null
      ? (data.value as SelectItem).value
      : data.value;
  },
  set(value) {
    data.value = value;
  },
});
</script>

<template>
  <div class="setting-item">
    <AbField
      :label="label"
      :description="description"
      :error="error"
      :required="required"
    >
      <AbSwitch
        v-if="type === 'switch'"
        v-model="data"
        :class="css"
        :aria-label="labelText"
      />

      <AbSelect
        v-else-if="type === 'select'"
        v-model="selectValue"
        :items="prop?.items ?? []"
        :class="css"
        class="setting-select"
        :aria-label="labelText"
      />

      <AbInput
        v-else-if="type === 'input'"
        v-model="data"
        :class="css"
        :type="prop?.type"
        :placeholder="prop?.placeholder"
        :min="prop?.min"
        :max="prop?.max"
        :autocomplete="prop?.autocomplete"
      />

      <div v-else-if="type === 'dynamic-tags'" class="dynamic-tags-wrapper">
        <AbTagsInput
          v-model="data"
          :aria-label="labelText"
          :placeholder="prop?.placeholder"
        />
      </div>
    </AbField>

    <div v-if="bottomLine" class="setting-divider" />
  </div>
</template>

<style lang="scss" scoped>
.setting-item {
  width: 100%;

  // Prevent fixed-width inputs from causing horizontal overflow on mobile
  :deep(input),
  :deep(select),
  :deep(.n-select),
  :deep(.n-input),
  :deep(.ab-input) {
    max-width: 100%;
  }
}

.setting-divider {
  height: 1px;
  background: var(--color-border);
  margin-top: 12px;
}

// 与 ab-input 同宽（200px），各行控件左缘对齐；标签在框内换行
.dynamic-tags-wrapper {
  width: 100%;

  @include forTablet {
    width: 200px;
  }
}
</style>
