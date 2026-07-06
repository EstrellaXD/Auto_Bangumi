<script lang="ts" setup>
import { NDynamicTags } from 'naive-ui';
import { isObject } from 'radash';
import AbField from './basic/ab-field.vue';
import AbInput from './basic/ab-input.vue';
import AbSelect from './basic/ab-select.vue';
import AbSwitch from './basic/ab-switch.vue';
import type { AbSettingProps, SelectItem } from '#/components';

// 设置行：ab-field（标签/说明/错误/aria）+ 对应控件的组合。
const props = withDefaults(defineProps<AbSettingProps>(), {
  css: '',
  bottomLine: false,
  description: '',
  error: '',
  required: false,
});

const data = defineModel<any>('data');

const labelText = computed(() =>
  typeof props.label === 'function' ? props.label() : props.label
);

// 旧组件允许 v-model 绑定对象（SelectItem）；读取时取 .value，
// 写回时保持字符串（配置值均为字符串）
const selectValue = computed<string | number | null>({
  get() {
    return isObject(data.value) ? (data.value as SelectItem).value : data.value;
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
      ></AbSwitch>

      <AbSelect
        v-else-if="type === 'select'"
        v-model="selectValue"
        :items="prop?.items ?? []"
        :class="css"
        class="setting-select"
        :aria-label="labelText"
      ></AbSelect>

      <AbInput
        v-else-if="type === 'input'"
        v-model="data"
        :class="css"
        :type="prop?.type"
        :placeholder="prop?.placeholder"
        :min="prop?.min"
        :max="prop?.max"
      ></AbInput>

      <div v-else-if="type === 'dynamic-tags'" class="dynamic-tags-wrapper">
        <NDynamicTags
          v-model:value="data"
          size="small"
          :aria-label="labelText"
        ></NDynamicTags>
      </div>
    </AbField>

    <div v-if="bottomLine" class="setting-divider"></div>
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

.dynamic-tags-wrapper {
  width: 100%;
  overflow-x: auto;
  padding-bottom: 2px;

  @include forTablet {
    max-width: 220px;
  }
}
</style>
