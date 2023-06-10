<script lang="ts" setup>
import type { Downloader, DownloaderType } from '#/config';
import type { SettingItem } from '#/components';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });
const { getSettingGroup } = useConfigStore();

const downloader = getSettingGroup('downloader');
const downloaderType: DownloaderType = ['qbittorrent'];

const items: SettingItem<Downloader>[] = [
  {
    configKey: 'type',
    label: t('config.downloaderset.type'),
    type: 'select',
    css: 'w-115px',
    prop: {
      items: downloaderType,
    },
  },
  {
    configKey: 'host',
    label: t('config.downloaderset.host'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '127.0.0.1:8989',
    },
  },
  {
    configKey: 'username',
    label: t('config.downloaderset.username'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'admin',
    },
  },
  {
    configKey: 'password',
    label: t('config.downloaderset.password'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'admindmin',
    },
    bottomLine: true,
  },
  {
    configKey: 'path',
    label: t('config.downloaderset.path'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '/downloads/Bangumi',
    },
  },
  {
    configKey: 'ssl',
    label: t('config.downloaderset.ssl'),
    type: 'switch',
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.downloaderset.title')">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="downloader[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
