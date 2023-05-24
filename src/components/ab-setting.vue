<script lang="ts" setup>
import AbSwitch from '../basic/ab-switch.vue';
import AbSelect from '../basic/ab-select.vue';
import type { AbSettingProps } from '#/components';

withDefaults(defineProps<AbSettingProps>(), {
  css: '',
  bottomLine: false,
});

const data = defineModel<any>('data');
</script>

<template>
  <div>
    <ab-label :label="label">
      <ab-switch
        v-if="type === 'switch'"
        v-model:checked="data"
        v-bind="prop"
        :class="css"
      ></ab-switch>

      <ab-select
        v-else-if="type === 'select'"
        v-model="data"
        v-bind="prop"
        :class="css"
      ></ab-select>

      <input
        v-else-if="type === 'input'"
        v-model="data"
        ab-input
        :class="css"
        v-bind="prop"
      />
    </ab-label>

    <div v-if="bottomLine" line my-12px></div>
  </div>
</template>
