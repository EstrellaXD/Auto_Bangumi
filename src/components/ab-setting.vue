<script lang="ts" setup>
import AbSwitch from '../basic/ab-switch.vue';
import AbSelect from '../basic/ab-select.vue';
import type { AbSettingProps } from '#/components';
import { NDynamicTags } from 'naive-ui';

withDefaults(defineProps<AbSettingProps>(), {
  css: '',
  bottomLine: false,
});

const data = defineModel<any>('data');
</script>

<template>
  <div>
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

      <div max-w-200px v-else-if="type === 'dynamic-tags'">
        <n-dynamic-tags v-model:value="data" size="small"></n-dynamic-tags>
      </div>
    </ab-label>

    <div v-if="bottomLine" line my-12px></div>
  </div>
</template>
