<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';
import type { SettingItem } from '#/components';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });
const rule = defineModel<BangumiRule>('rule', {
  required: true,
});

const items: SettingItem<BangumiRule>[] = [
  {
    configKey: 'official_title',
    label: t('homepage.rule.officaltitle'),
    type: 'input',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'year',
    label: t('homepage.rule.year'),
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'season',
    label: t('homepage.rule.season'),
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
    },
    bottomLine: true,
  },
  {
    configKey: 'offset',
    label: t('homepage.rule.offset'),
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
    },
  },
  {
    configKey: 'filter',
    label: t('homepage.rule.exclude'),
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
