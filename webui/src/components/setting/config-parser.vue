<script lang="ts" setup>
import type {
  RssParser,
  RssParserLang,
  RssParserMethodType,
  RssParserType,
} from '#/config';
import type { SettingItem } from '#/components';
import { useI18n } from 'vue-i18n';

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
    label: t('config.parserset.enable'),
    type: 'switch',
  },
  {
    configKey: 'type',
    label: t('config.parserset.source'),
    type: 'select',
    css: 'w-115px',
    prop: {
      items: sourceItems,
    },
  },
  {
    configKey: 'token',
    label: t('config.parserset.token'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'token',
    },
  },
  {
    configKey: 'custom_url',
    label: t('config.parserset.url'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'mikanime.tv',
    },
    bottomLine: true,
  },
  {
    configKey: 'language',
    label: t('config.parserset.language'),
    type: 'select',
    prop: {
      items: langs,
    },
  },
  {
    configKey: 'parser_type',
    label: t('config.parserset.type'),
    type: 'select',
    prop: {
      items: parserMethods,
    },
  },
  {
    configKey: 'filter',
    label: t('config.parserset.exclude'),
    type: 'dynamic-tags',
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.parserset.title')">
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
