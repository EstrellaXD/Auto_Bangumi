<script lang="ts" setup>
import type {
  RssParser,
  RssParserLang,
  RssParserMethodType,
  RssParserType,
} from '#/config';
import type { SettingItem } from '#/components';

const { getSettingGroup } = useConfigStore();

const parser = getSettingGroup('rss_parser');

const sourceItems: RssParserType = ['mikan'];
const langs: RssParserLang = ['zh', 'en', 'jp'];
/** @ts-expect-error Incorrect order */
const parserMethods: RssParserMethodType = ['tmdb', 'mikan', 'parser'];

const items: SettingItem<RssParser>[] = [
  {
    configKey: 'enable',
    label: 'Enable',
    type: 'switch',
  },
  {
    configKey: 'type',
    label: 'Source',
    type: 'select',
    css: 'w-115px',
    prop: {
      items: sourceItems,
    },
  },
  {
    configKey: 'token',
    label: 'Token',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'token',
    },
  },
  {
    configKey: 'custom_url',
    label: 'Custom Url',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'mikanime.tv',
    },
    bottomLine: true,
  },
  {
    configKey: 'language',
    label: 'Language',
    type: 'select',
    prop: {
      items: langs,
    },
  },
  {
    configKey: 'parser_type',
    label: 'Parser Type',
    type: 'select',
    prop: {
      items: parserMethods,
    },
  },
  {
    configKey: 'filter',
    label: 'Exclude',
    type: 'dynamic-tags',
  },
];
</script>

<template>
  <ab-fold-panel title="Parser Setting">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="parser[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
