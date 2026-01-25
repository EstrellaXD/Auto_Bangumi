<script lang="ts" setup>
import { NDynamicTags } from 'naive-ui';
import type { AbSettingProps } from '#/components';

withDefaults(defineProps<AbSettingProps>(), {
  css: '',
  bottomLine: false,
});

 
const data = defineModel<any>('data');
</script>

<template>
  <div class="setting-item">
    <ab-label :label="label">
      <AbSwitch
        v-if="type === 'switch'"
        v-model:checked="data"
        v-bind="prop"
        :class="css"
      ></AbSwitch>

      <AbSelect
        v-else-if="type === 'select'"
        v-model="data"
        v-bind="prop"
        :class="css"
      ></AbSelect>

      <input
        v-else-if="type === 'input'"
        v-model="data"
        ab-input
        :class="css"
        v-bind="prop"
      />

      <div v-else-if="type === 'dynamic-tags'" class="dynamic-tags-wrapper">
        <NDynamicTags v-model:value="data" size="small"></NDynamicTags>
      </div>
    </ab-label>

    <div v-if="bottomLine" class="setting-divider"></div>
  </div>
</template>

<style lang="scss" scoped>
.setting-item {
  width: 100%;
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
