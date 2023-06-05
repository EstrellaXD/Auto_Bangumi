<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';
import type { SettingItem } from '#/components';

const rule = defineModel<BangumiRule>('rule', {
  required: true,
});

const items: SettingItem<BangumiRule>[] = [
  {
    configKey: 'official_title',
    label: 'Officical Ttile',
    type: 'input',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'year',
    label: 'Year',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'season',
    label: 'Season',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
    },
    bottomLine: true,
  },
  {
    configKey: 'offset',
    label: 'Offset',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
    },
  },
  {
    configKey: 'filter',
    label: 'Exclude',
    type: 'dynamic-tags',
    bottomLine: true,
  },
];
</script>

<template>
  <div space-y-12px>
    <ab-setting
      v-for="i in items"
      :key="i.configKey"
      v-bind="i"
      v-model:data="rule[i.configKey]"
    ></ab-setting>
  </div>
</template>
