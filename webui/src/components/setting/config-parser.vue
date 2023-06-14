<script lang="ts" setup>
import { useI18n } from 'vue-i18n';
import type {
  RssParser,
  RssParserLang,
  RssParserMethodType,
  RssParserType,
} from '#/config';
import type { SettingItem } from '#/components';

const { t } = useI18n({ useScope: 'global' });
const { getSettingGroup } = useConfigStore();

const parser = getSettingGroup('rss_parser');

const sourceItems: RssParserType = ['mikan'];
const langs: RssParserLang = ['zh', 'en', 'jp'];
/** @ts-expect-error Incorrect order */
const parserMethods: RssParserMethodType = ['tmdb', 'mikan', 'parser'];

const items: SettingItem<RssParser>[] = [
  {
    configKey: 'enable',
    label: t('config.parser_set.enable'),
    type: 'switch',
  },
  {
    configKey: 'type',
    label: t('config.parser_set.source'),
    type: 'select',
    css: 'w-115px',
    prop: {
      items: sourceItems,
    },
  },
  {
    configKey: 'token',
    label: t('config.parser_set.token'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'token',
    },
  },
  {
    configKey: 'custom_url',
    label: t('config.parser_set.url'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'mikanime.tv',
    },
    bottomLine: true,
  },
  {
    configKey: 'language',
    label: t('config.parser_set.language'),
    type: 'select',
    prop: {
      items: langs,
    },
  },
  {
    configKey: 'parser_type',
    label: t('config.parser_set.type'),
    type: 'select',
    prop: {
      items: parserMethods,
    },
  },
  {
    configKey: 'filter',
    label: t('config.parser_set.exclude'),
    type: 'dynamic-tags',
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.parser_set.title')">
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
