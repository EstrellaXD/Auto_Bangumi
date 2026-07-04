<script lang="ts" setup>
import { useId } from 'vue';
import { NDynamicTags, NSelect, NSwitch } from 'naive-ui';
import { isObject } from 'radash';
import type { SelectOption } from 'naive-ui';
import type { AbSettingProps, SelectItem } from '#/components';

const props = withDefaults(defineProps<AbSettingProps>(), {
  css: '',
  bottomLine: false,
});


const data = defineModel<any>('data');

// 每个设置项一对稳定 id：原生 input 用 <label for>，
// naive-ui 组件（无法透传 id 到焦点元素）用 aria-label/aria-labelledby
const controlId = useId();
const labelId = useId();

const labelText = computed(() =>
  typeof props.label === 'function' ? props.label() : props.label
);

// 旧 AbSelect 接受 items: Array<SelectItem | string>；NSelect 需要
// options: Array<{ label, value }>，这里做一层适配
const selectOptions = computed<SelectOption[]>(() => {
  const items: Array<SelectItem | string> = props.prop?.items ?? [];
  return items.map((item) =>
    isObject(item)
      ? { label: item.label ?? item.value, value: item.value }
      : { label: item, value: item }
  );
});

// 旧组件允许 v-model 绑定对象（SelectItem）；NSelect 只接受基础类型，
// 读取时取 .value，写回时保持字符串（配置值均为字符串）
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
    <ab-label
      :label="label"
      :for-id="type === 'input' ? controlId : undefined"
      :label-id="labelId"
    >
      <NSwitch
        v-if="type === 'switch'"
        v-model:value="data"
        :class="css"
        :aria-label="labelText"
        :aria-labelledby="labelId"
      ></NSwitch>

      <NSelect
        v-else-if="type === 'select'"
        v-model:value="selectValue"
        :options="selectOptions"
        :class="css"
        class="setting-select"
        :aria-label="labelText"
      ></NSelect>

      <input
        v-else-if="type === 'input'"
        :id="controlId"
        v-model="data"
        ab-input
        :class="css"
        v-bind="prop"
      />

      <div v-else-if="type === 'dynamic-tags'" class="dynamic-tags-wrapper">
        <NDynamicTags
          v-model:value="data"
          size="small"
          :aria-label="labelText"
        ></NDynamicTags>
      </div>
    </ab-label>

    <div v-if="bottomLine" class="setting-divider"></div>
  </div>
</template>

<style lang="scss" scoped>
.setting-item {
  width: 100%;

  // 无宽度 class 的下拉框给一个下限，避免窄到只剩箭头
  .setting-select {
    min-width: 140px;
  }

  // Prevent fixed-width inputs from causing horizontal overflow on mobile
  :deep(input),
  :deep(select),
  :deep(.n-select),
  :deep(.n-input) {
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
